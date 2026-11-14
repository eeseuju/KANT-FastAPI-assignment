from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from app.schemas.user import UserPublic


CommentContent = Annotated[
    str, 
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


# 댓글 작성
class CommentCreate(BaseModel):

    content: CommentContent = Field(description='댓글 내용(1~1000자)', examples=['확인했습니다.'])


# 댓글 조회
class CommentRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    author: UserPublic
    content: str
    created_at: datetime