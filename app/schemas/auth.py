from pydantic import BaseModel, Field

# 로그인 성공 응답
class TokenResponse(BaseModel):

    access_token: str = Field(description='JWT 액세스 토큰')
    token_type: str = Field(default='bearer', description='토큰 종류(bearer)')