from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.errors import ConflictError, UnauthorizedError, error_responses
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate, UserRead


router = APIRouter(prefix='/auth', tags=['auth'], responses=error_responses(401, 409))


DUPLICATE_MESSAGE = '이미 사용 중인 이메일 또는 닉네임입니다.'


@router.post(
    '/signup',
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary='회원가입',
)
def signup(body: UserCreate, db: Session = Depends(get_db)):
    '''이메일과 닉네임으로 가입합니다.

    - 이메일은 소문자로 저장되며, 대소문자를 구분하지 않고 중복을 검사합니다.
    - 비밀번호는 bcrypt로 해싱해 저장하며 응답에는 포함되지 않습니다.
    - 이미 사용 중인 이메일 또는 닉네임이면 `409`(`USER_ALREADY_EXISTS`)를 돌려줍니다.
    '''
    email = body.email.lower()
    exists = db.scalar(
        select(User).where(or_(User.email == email, User.username == body.username))
    )
    if exists:
        raise ConflictError(DUPLICATE_MESSAGE, code='USER_ALREADY_EXISTS')

    user = User(
        email=email,
        username=body.username,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(DUPLICATE_MESSAGE, code='USER_ALREADY_EXISTS')
    db.refresh(user)
    return user


@router.post('/login', response_model=TokenResponse, summary='로그인(JWT 발급)')
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    '''이메일과 비밀번호로 로그인하고 JWT 액세스 토큰을 받습니다.

    - 요청은 JSON이 아니라 **폼 데이터**입니다. `username` 칸에 **이메일**을 입력하세요.
    - 토큰은 발급 후 30분 동안 유효합니다.
    - 받은 토큰은 `Authorization: Bearer <토큰>` 헤더로 보냅니다(Swagger에서는 **Authorize** 버튼).
    - 이메일과 비밀번호 중 어느 쪽이 틀렸는지는 알려 주지 않습니다(`INVALID_CREDENTIALS`).
    '''
    # 폼의 username 칸에 이메일을 입력
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise UnauthorizedError('이메일 또는 비밀번호가 올바르지 않습니다.', code='INVALID_CREDENTIALS')
    return TokenResponse(access_token=create_access_token(user.id))