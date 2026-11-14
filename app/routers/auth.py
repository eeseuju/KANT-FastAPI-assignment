from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate, UserRead


router = APIRouter(prefix='/auth', tags=['auth'])


DUPLICATE_MESSAGE = '이미 사용 중인 이메일 또는 닉네임입니다.'


@router.post(
    '/signup',
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary='회원가입',
)
def signup(body: UserCreate, db: Session = Depends(get_db)):
    email = body.email.lower()
    exists = db.scalar(
        select(User).where(or_(User.email == email, User.username == body.username))
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_MESSAGE)

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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_MESSAGE)
    db.refresh(user)
    return user


@router.post('/login', response_model=TokenResponse, summary='로그인(JWT 발급)')
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 폼의 username 칸에 이메일을 입력
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='이메일 또는 비밀번호가 올바르지 않습니다.',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return TokenResponse(access_token=create_access_token(user.id))