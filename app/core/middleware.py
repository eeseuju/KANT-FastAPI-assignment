import logging
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


logger = logging.getLogger('app.access')


def register_middlewares(app: FastAPI) -> None:
    # 먼저 등록한 미들웨어가 안쪽, 나중에 등록한 것이 바깥쪽이다.
    # 요청은 바깥 → 안쪽으로 들어가고, 응답은 안쪽 → 바깥으로 나온다.
    @app.middleware('http')
    async def access_log(request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]  # 이 요청을 구분하는 짧은 번호
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.error(
                '%s %s -> 처리되지 않은 오류 (%.1fms) id=%s',
                request.method, request.url.path, elapsed_ms, request_id,
            )
            raise  # 응답은 U10의 전역 핸들러가 만든다.
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Process-Time'] = f'{elapsed_ms:.1f}ms'
        # 주소(path)만 남긴다. 헤더(토큰)·본문(비밀번호)·쿼리 문자열은 기록하지 않는다.
        logger.info(
            '%s %s -> %s (%.1fms) id=%s',
            request.method, request.url.path, response.status_code, elapsed_ms, request_id,
        )
        return response

    # CORS: 가장 바깥쪽에 둬서 사전 요청(OPTIONS)에도, 오류 응답에도 헤더가 붙게 한다.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,  # 쿠키가 아니라 Authorization 헤더로 인증하므로 필요 없다.
        allow_methods=['GET', 'POST', 'PATCH', 'DELETE'],
        allow_headers=['Authorization', 'Content-Type'],
        expose_headers=['X-Request-ID', 'X-Cache'],  # 브라우저 JS가 읽을 수 있게 허용
    )