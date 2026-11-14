import logging
from typing import Any
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger('app.errors')


# ---------- 응답 모양 ----------
class ErrorDetail(BaseModel):
    field: str = Field(description='문제가 된 입력 위치(예: body.title)')
    message: str = Field(description='그 입력의 문제 설명')


class ErrorBody(BaseModel):
    code: str = Field(description='오류 종류를 나타내는 고정 코드', examples=['POST_NOT_FOUND'])
    message: str = Field(description='사람이 읽는 설명')
    details: list[ErrorDetail] | None = Field(default=None, description='입력 오류일 때 항목별 설명')


# 모든 오류 응답이 따르는 공통 형식
class ErrorResponse(BaseModel):

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {'error': {'code': 'POST_NOT_FOUND', 'message': '게시글을 찾을 수 없습니다.', 'details': None}},
                {
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': '입력값이 올바르지 않습니다.',
                        'details': [{'field': 'body.title', 'message': 'String should have at least 1 character'}],
                    }
                },
            ]
        }
    )

    error: ErrorBody


# ---------- 고의 오류 ----------
class AppError(Exception):

    status_code: int = 500
    code: str = 'INTERNAL_ERROR'

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.headers = headers


class UnauthorizedError(AppError):
    status_code = 401
    code = 'UNAUTHORIZED'

    def __init__(self, message: str = '로그인이 필요합니다.', *, code: str | None = None) -> None:
        # 401에는 "Bearer 토큰으로 인증하라"는 안내 헤더를 붙이는 것이 표준 규칙이다.
        super().__init__(message, code=code, headers={'WWW-Authenticate': 'Bearer'})


class ForbiddenError(AppError):
    status_code = 403
    code = 'FORBIDDEN'


class NotFoundError(AppError):
    status_code = 404
    code = 'NOT_FOUND'


class ConflictError(AppError):
    status_code = 409
    code = 'CONFLICT'


class PayloadTooLargeError(AppError):
    status_code = 413
    code = 'PAYLOAD_TOO_LARGE'


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = 'UNSUPPORTED_MEDIA_TYPE'


# ---------- 문서용 코드 정리 ----------
_DESCRIPTIONS = {
    401: '인증 실패(로그인 필요·토큰 오류)',
    403: '권한 없음(작성자가 아님)',
    404: '대상을 찾을 수 없음',
    409: '이미 존재함(중복)',
    413: '파일이 너무 큼',
    415: '지원하지 않는 파일 종류',
    422: '입력값 오류',
    500: '서버 내부 오류',
}


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    return {c: {'model': ErrorResponse, 'description': _DESCRIPTIONS[c]} for c in codes}


# ---------- 같은 모양 핸들러 ----------
def _json_error(
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode='json'), headers=headers)


_HTTP_CODES = {
    400: 'BAD_REQUEST',
    401: 'UNAUTHORIZED',
    403: 'FORBIDDEN',
    404: 'NOT_FOUND',
    405: 'METHOD_NOT_ALLOWED',
    409: 'CONFLICT',
    413: 'PAYLOAD_TOO_LARGE',
    415: 'UNSUPPORTED_MEDIA_TYPE',
    422: 'VALIDATION_ERROR',
    429: 'TOO_MANY_REQUESTS',
}


# FastAPI/Starlette가 기본으로 뱉는 영어 메시지를 한글로 바꾼다.
_KOREAN = {
    'Not authenticated': '로그인이 필요합니다.',
    'Not Found': '요청한 주소를 찾을 수 없습니다.',
    'Method Not Allowed': '허용되지 않는 메서드입니다.',
}


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return _json_error(exc.status_code, exc.code, exc.message, headers=exc.headers)


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # 없는 주소(404), 허용 안 된 메서드(405), 토큰 헤더 없음(401) 등 프레임워크가 내는 오류
    detail = exc.detail if isinstance(exc.detail, str) else 'HTTP 오류'
    return _json_error(
        exc.status_code,
        _HTTP_CODES.get(exc.status_code, 'HTTP_ERROR'),
        _KOREAN.get(detail, detail),
        headers=dict(exc.headers) if exc.headers else None,
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # 기본 응답은 사용자가 보낸 값(input)을 그대로 되돌려 준다. 비밀번호가 새지 않도록 한다.
    details = [
        ErrorDetail(
            field='.'.join(str(part) for part in err['loc']),
            message=err['msg'].removeprefix('Value error, '),
        )
        for err in exc.errors()
    ]
    return _json_error(422, 'VALIDATION_ERROR', '입력값이 올바르지 않습니다.', details=details)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # 원인은 서버 로그에만 남기고, 사용자에게는 내부 정보를 보여 주지 않는다.
    logger.error('처리되지 않은 오류: %s %s', request.method, request.url.path, exc_info=exc)
    return _json_error(500, 'INTERNAL_ERROR', '서버 내부 오류가 발생했습니다.')


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)