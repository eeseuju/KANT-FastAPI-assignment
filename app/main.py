from fastapi import FastAPI
from app.routers import auth, health, users


app = FastAPI(
    title='Board API',
    description='회원가입·로그인(JWT)과 게시글·댓글을 제공하는 게시판 REST API',
    version='0.1.0',
)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)