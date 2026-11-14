from datetime import datetime
from typing import Annotated
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)


Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=20, pattern=r'^\w+$'),
]


# 회원가입 요청
class UserCreate(BaseModel):

    email: EmailStr = Field(description='로그인에 쓰는 이메일', examples=['user@example.com'])
    username: Username = Field(description='닉네임(2~20자, 글자·숫자·밑줄)', examples=['kant_user'])
    password: str = Field(min_length=8, max_length=72, description='비밀번호(8~72자)', examples=['password1234'])

    @field_validator('password')
    @classmethod
    def password_byte_limit(cls, v: str) -> str:
        # bcrypt는 72바이트까지만 처리한다. 한글은 글자당 3바이트라 따로 검사한다.
        if len(v.encode('utf-8')) > 72:
            raise ValueError('비밀번호는 72바이트를 넘을 수 없습니다.')
        return v


# 다른 사람에게 보여 줘도 되는 사용자 정보(이메일 제외)
class UserPublic(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


# 본인에게 돌려주는 사용자 정보
class UserRead(UserPublic):

    email: EmailStr
    created_at: datetime