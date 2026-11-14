from fastapi import APIRouter, Depends
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserRead


router = APIRouter(prefix='/users', tags=['users'])


@router.get('/me', response_model=UserRead, summary='내 정보 조회(로그인 필요)')
def read_me(current_user: User = Depends(get_current_user)):
    return current_user