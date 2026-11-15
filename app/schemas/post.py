from datetime import datetime
from enum import Enum
from typing import Annotated, Self
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from app.schemas.user import UserPublic


# 게시글 분류 (4가지만 허용)
class PostCategory(str, Enum):

    NOTICE = '공지'
    EVENT = '이벤트'
    INQUIRY = '고객문의'
    COMMUNITY = '커뮤니티'


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


# 글 작성
class PostCreate(BaseModel):

    category: PostCategory = Field(description='게시글 분류')
    title: Title = Field(description='제목(1~200자)', examples=['9/17(목) 정기점검 안내'])
    content: Content = Field(description='본문(1~10000자)', examples=['점검 시간은 오전 6시~10시입니다.'])


# 글 수정 (바꿀 항목만 보냄)
class PostUpdate(BaseModel):

    category: PostCategory | None = Field(default=None, description='바꿀 분류')
    title: Title | None = Field(default=None, description='바꿀 제목')
    content: Content | None = Field(default=None, description='바꿀 본문')

    @model_validator(mode='after')
    def check_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError('수정할 항목을 하나 이상 보내야 합니다.')
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f'{name} 항목은 null일 수 없습니다.')
        return self


# 글 조회
class PostRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: PostCategory
    title: str
    content: str
    image_path: str | None
    author: UserPublic
    created_at: datetime
    updated_at: datetime


# 글 목록 조회
class PostListResponse(BaseModel):

    items: list[PostRead]
    total: int = Field(description='조건에 맞는 전체 글 수')
    page: int = Field(description='현재 페이지(1부터)')
    size: int = Field(description='페이지당 글 수')
    pages: int = Field(description='전체 페이지 수')
