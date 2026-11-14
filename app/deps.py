import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User


# tokenUrl: Swagger의 Authorize 버튼이 로그인 요청을 보낼 주소
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


# Authorization 헤더의 토큰으로 현재 로그인한 사용자 탐색
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload['sub'])
    except jwt.ExpiredSignatureError:
        # code가 TOKEN_EXPIRED라서 프론트가 "다시 로그인" 화면으로 보낼 수 있다
        raise UnauthorizedError('토큰이 만료되었습니다. 다시 로그인하세요.', code='TOKEN_EXPIRED')
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise UnauthorizedError('유효하지 않은 토큰입니다.', code='INVALID_TOKEN')

    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError('유효하지 않은 토큰입니다.', code='INVALID_TOKEN')
    return user