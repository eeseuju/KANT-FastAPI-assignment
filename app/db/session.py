from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings


# pool_pre_ping: 끊긴 연결을 쓰기 전에 확인해서 오류를 줄인다.
# connect_timeout: DB에 5초 안에 못 붙으면 포기한다. 무한정 기다리며 서버가 멈춘 것처럼 보이는 것을 막는다.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={'connect_timeout': 5},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# 요청 하나당 세션 하나를 열고 끝나면 닫는다.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()