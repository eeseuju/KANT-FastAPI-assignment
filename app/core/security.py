from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from app.core.config import settings


# 비밀번호를 bcrypt로 해싱
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# 입력 비밀번호와 저장된 해시 비교
def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # bcrypt는 72바이트를 넘는 비밀번호를 거부한다. 그런 입력은 틀린 비밀번호로 취급한다.
        return False


# JWT 생성
def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    minutes = settings.access_token_expire_minutes if expires_minutes is None else expires_minutes
    payload = {
        'sub': str(user_id),
        'iat': now,
        'exp': now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# JWT 서명 및 만료 확인
def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])