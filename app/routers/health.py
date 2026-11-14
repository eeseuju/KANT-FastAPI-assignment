from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.health import HealthResponse


router = APIRouter(tags=['health'])


@router.get(
    '/health',
    response_model=HealthResponse,
    summary='서버·DB 상태 확인',
    responses={503: {'model': HealthResponse, 'description': 'DB에 연결할 수 없음'}},
)
def health(db: Session = Depends(get_db)):
    '''서버와 DB가 정상인지 확인합니다. DB에 연결할 수 없으면 `503`을 돌려줍니다.'''
    # DB를 쓰므로 def로 쓴다
    # 서버가 다른 요청을 계속 받을 수 있게 별도 스레드에서 실행된다.
    try:
        db.execute(text('select 1'))
    except SQLAlchemyError:
        # 로드밸런서·모니터링이 "이 서버는 지금 쓰면 안 된다"를 알 수 있게 503으로 답한다.
        return JSONResponse(status_code=503, content={'status': 'error', 'database': 'unavailable'})
    return HealthResponse(status='ok', database='ok')