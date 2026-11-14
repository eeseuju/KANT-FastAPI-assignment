import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User


# tokenUrl: Swagger의 Authorize 버튼이 로그인 요청을 보낼 주소
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


# 401(인증 실패) 오류 발생기 (raise는 부르는 쪽에서)
def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={'WWW-Authenticate': 'Bearer'},
    )


# Authorization 헤더의 토큰으로 현재 로그인 사용자 탐색
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload['sub'])
    except jwt.ExpiredSignatureError:
        raise _unauthorized('토큰이 만료되었습니다. 다시 로그인하세요.')
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _unauthorized('유효하지 않은 토큰입니다.')

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized('유효하지 않은 토큰입니다.')
    return user