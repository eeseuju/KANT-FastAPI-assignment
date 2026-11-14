from pydantic import BaseModel, Field


# 서버 상태 확인 응답
class HealthResponse(BaseModel):

    status: str = Field(description='전체 상태(ok 또는 error)', examples=['ok'])
    database: str = Field(description='DB 연결 상태(ok 또는 unavailable)', examples=['ok'])