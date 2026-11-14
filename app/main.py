from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.logging_config import setup_logging
from app.core.middleware import register_middlewares
from app.core.storage import UPLOAD_DIR
from app.core.errors import error_responses, register_exception_handlers
from app.routers import auth, comments, health, home, posts, uploads, users


UPLOAD_DIR.mkdir(exist_ok=True)  # StaticFiles는 폴더가 이미 있어야 한다.

setup_logging()  # app을 만들기 전에 호출

DESCRIPTION = '''
회원가입·로그인(JWT)과 게시글·댓글을 제공하는 게시판 REST API입니다.

## 사용 방법
1. `POST /auth/signup`으로 가입합니다.
2. 오른쪽 위 **Authorize** 버튼을 눌러 이메일(`username` 칸)과 비밀번호를 입력합니다.
3. 자물쇠 표시가 있는 API를 바로 시험해 볼 수 있습니다.

## 오류 응답
모든 오류는 `{"error": {"code", "message", "details"}}` 형식입니다. `code`는 프로그램이 읽는 고정 이름이고, `message`는 사람이 읽는 설명입니다.
'''


# Swagger 화면에서 이 순서대로 묶여 보인다.
TAGS = [
    {'name': 'auth', 'description': '회원가입과 로그인(JWT 발급)'},
    {'name': 'users', 'description': '내 정보'},
    {'name': 'posts', 'description': '게시글 CRUD, 목록 페이지네이션·검색·분류 거르기. 목록·상세는 30초 캐시(`X-Cache` 헤더)'},
    {'name': 'comments', 'description': '댓글 작성·목록·삭제'},
    {'name': 'uploads', 'description': '게시글 이미지 업로드(jpg/png/gif/webp, 최대 5MB)'},
    {'name': 'health', 'description': '서버·DB 상태 확인'},
]


app = FastAPI(
    title='Board API',
    description=DESCRIPTION,
    openapi_tags=TAGS,
    version='0.1.0',
    responses=error_responses(422, 500),  # 모든 API에 공통으로 문서에 표시
)


app.include_router(home.router)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(uploads.router)
app.mount('/uploads', StaticFiles(directory=UPLOAD_DIR), name='uploads')

register_exception_handlers(app)
register_middlewares(app)  