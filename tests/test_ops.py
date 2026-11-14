import logging
import re
import time

from sqlalchemy.exc import OperationalError

from app.core.cache import post_cache
from app.db.session import get_db
from app.main import app


ORIGIN = 'http://localhost:3000'


# ---------- 헬스체크 ----------
def test_health_ok(client):
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json() == {'status': 'ok', 'database': 'ok'}


def test_health_returns_503_when_database_is_down(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError('select 1', {}, Exception('db down'))

        def close(self):
            pass

    def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    r = client.get('/health')
    assert r.status_code == 503
    assert r.json() == {'status': 'error', 'database': 'unavailable'}


# ---------- 요청 로깅 미들웨어 ----------
def test_every_response_has_request_id_and_process_time(client):
    for path in ('/health', '/no-such-path', '/users/me'):  # 성공·404·401 모두
        r = client.get(path)
        assert re.fullmatch(r'[0-9a-f]{12}', r.headers['x-request-id'])
        assert re.fullmatch(r'\d+\.\d+ms', r.headers['x-process-time'])
    assert client.get('/health').headers['x-request-id'] != client.get('/health').headers['x-request-id']


def test_access_log_has_same_id_and_hides_secrets(client, alice, caplog):
    with caplog.at_level(logging.INFO, logger='app.access'):
        r = client.get('/posts', params={'q': 'secret-keyword'}, headers=alice)
    # 테스트 도구(httpx)가 남기는 로그는 빼고, 우리 앱의 접속 로그(app.access)만 본다.
    text = '\n'.join(rec.getMessage() for rec in caplog.records if rec.name == 'app.access')
    assert f"id={r.headers['x-request-id']}" in text  # 응답 헤더와 같은 번호
    assert 'GET /posts -> 200' in text
    assert alice['Authorization'].split()[1] not in text  # 토큰은 기록하지 않는다.
    assert 'secret-keyword' not in text  # 쿼리 문자열도 기록하지 않는다.


# ---------- CORS ----------
def test_cors_preflight_allowed_origin(client):
    r = client.options(
        '/posts',
        headers={
            'Origin': ORIGIN,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'authorization,content-type',
        },
    )
    assert r.status_code == 200
    assert r.headers['access-control-allow-origin'] == ORIGIN
    assert 'POST' in r.headers['access-control-allow-methods']
    assert 'authorization' in r.headers['access-control-allow-headers'].lower()
    assert 'access-control-allow-credentials' not in r.headers


def test_cors_rejects_unknown_origin(client):
    r = client.options(
        '/posts', headers={'Origin': 'http://evil.example', 'Access-Control-Request-Method': 'POST'}
    )
    assert r.status_code == 400
    assert 'access-control-allow-origin' not in r.headers
    plain = client.get('/health', headers={'Origin': 'http://evil.example'})
    assert 'access-control-allow-origin' not in plain.headers


def test_cors_headers_are_also_on_error_responses(client):
    r = client.get('/posts/999999', headers={'Origin': ORIGIN})
    assert r.status_code == 404
    assert r.headers['access-control-allow-origin'] == ORIGIN


# ---------- 캐시 ----------
def test_list_cache_hit_and_miss_by_parameters(client, alice, make_post):
    make_post(alice)
    assert client.get('/posts').headers['x-cache'] == 'MISS'
    assert client.get('/posts').headers['x-cache'] == 'HIT'
    assert client.get('/posts', params={'size': 1}).headers['x-cache'] == 'MISS'  # 조건이 다르면 다른 캐시


def test_cache_returns_same_body_on_hit(client, alice, make_post):
    make_post(alice)
    first = client.get('/posts')
    second = client.get('/posts')
    assert second.headers['x-cache'] == 'HIT' and first.json() == second.json()


def test_create_invalidates_list_cache(client, alice, make_post):
    make_post(alice)
    assert client.get('/posts').json()['total'] == 1
    make_post(alice, title='두번째')
    r = client.get('/posts')
    assert r.headers['x-cache'] == 'MISS' and r.json()['total'] == 2  # 옛 목록이 아님


def test_patch_invalidates_detail_and_list_cache(client, alice, make_post):
    post = make_post(alice)
    url = f"/posts/{post['id']}"
    assert client.get(url).headers['x-cache'] == 'MISS'
    assert client.get(url).headers['x-cache'] == 'HIT'
    client.get('/posts')
    client.patch(url, headers=alice, json={'title': '새 제목'})
    detail = client.get(url)
    assert detail.headers['x-cache'] == 'MISS' and detail.json()['title'] == '새 제목'
    listing = client.get('/posts')
    assert listing.headers['x-cache'] == 'MISS' and listing.json()['items'][0]['title'] == '새 제목'


def test_delete_invalidates_cache_and_errors_are_not_cached(client, alice, make_post):
    post = make_post(alice)
    url = f"/posts/{post['id']}"
    client.get(url)
    client.delete(url, headers=alice)
    first, second = client.get(url), client.get(url)
    assert first.status_code == second.status_code == 404
    assert 'x-cache' not in first.headers and 'x-cache' not in second.headers  # 오류는 캐시하지 않는다.
    assert client.get('/posts', params={'size': 0}).status_code == 422


def test_image_upload_invalidates_cache(client, alice, make_post):
    post = make_post(alice)
    url = f"/posts/{post['id']}"
    client.get(url)
    png = b'\x89PNG\r\n\x1a\n' + b'0' * 32
    client.post(f'{url}/image', headers=alice, files={'file': ('a.png', png, 'image/png')})
    detail = client.get(url)
    assert detail.headers['x-cache'] == 'MISS' and detail.json()['image_path']


def test_cache_entries_expire_after_ttl(client, alice, make_post, monkeypatch):
    make_post(alice)
    monkeypatch.setattr(post_cache, 'ttl_seconds', 0.2)
    assert client.get('/posts').headers['x-cache'] == 'MISS'
    assert client.get('/posts').headers['x-cache'] == 'HIT'
    time.sleep(0.3)
    assert client.get('/posts').headers['x-cache'] == 'MISS'