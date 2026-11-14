from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.storage import UPLOAD_DIR
from app.routers import auth, comments, health, posts, uploads, users


UPLOAD_DIR.mkdir(exist_ok=True)  # StaticFiles는 폴더가 이미 있어야 한다.

app = FastAPI(
    title='Board API',
    description='회원가입·로그인(JWT)과 게시글·댓글을 제공하는 게시판 REST API',
    version='0.1.0',
)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(uploads.router)
app.mount('/uploads', StaticFiles(directory=UPLOAD_DIR), name='uploads')