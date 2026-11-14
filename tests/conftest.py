import os

# 테스트는 실제 DB(Supabase)를 절대 건드리지 않는다.
# app을 불러오기 전에 설정값을 덮어쓴다.
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-pytest-only-0123456789abcdef'
os.environ['CACHE_TTL_SECONDS'] = '30'

import bcrypt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401  (모델을 불러와야 테이블 등록 가능)
from app.core import storage  # noqa: E402
from app.core.cache import post_cache  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


PASSWORD = 'password1234'


# 테스트에서는 해싱 비용을 낮춰 빠르게 돌린다.
@pytest.fixture(autouse=True)
def fast_bcrypt(monkeypatch):
    real_gensalt = bcrypt.gensalt
    monkeypatch.setattr(bcrypt, 'gensalt', lambda: real_gensalt(rounds=4))


# 테스트마다 새로 만드는 메모리 DB (테스트 종료 시 소멸)
@pytest.fixture()
def session_factory():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,  # 모든 요청이 같은 메모리 DB를 보게 한다.
    )

    @event.listens_for(engine, 'connect')
    def _enable_foreign_keys(dbapi_connection, _):
        # SQLite는 기본으로 외래키(CASCADE)를 끄고 있어서 켜 준다.
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def client(session_factory, tmp_path, monkeypatch):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db  # 앱이 테스트 DB를 쓰게 바꾼다.
    monkeypatch.setattr(storage, 'UPLOAD_DIR', tmp_path)  # 업로드 파일은 임시 폴더에 저장
    post_cache.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    post_cache.clear()


# 가입과 로그인 후 Authorization 헤더 반환
def make_headers(client, name):
    r = client.post(
        '/auth/signup',
        json={'email': f'{name}@example.com', 'username': name, 'password': PASSWORD},
    )
    assert r.status_code == 201, r.text
    r = client.post('/auth/login', data={'username': f'{name}@example.com', 'password': PASSWORD})
    assert r.status_code == 200, r.text
    return {'Authorization': f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def alice(client):
    return make_headers(client, 'alice')


@pytest.fixture()
def bob(client):
    return make_headers(client, 'bob')


@pytest.fixture()
def make_post(client):
    def _make(headers, title='제목', category='공지', content='본문'):
        r = client.post(
            '/posts',
            headers=headers,
            json={'category': category, 'title': title, 'content': content},
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _make