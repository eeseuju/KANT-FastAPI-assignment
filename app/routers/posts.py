from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from app.core.cache import post_cache
from app.core.errors import ForbiddenError, NotFoundError, error_responses
from app.core.storage import delete_image
from app.db.session import get_db
from app.deps import get_current_user
from app.models.post import Post
from app.models.user import User
from app.schemas.post import (
    PostCategory,
    PostCreate,
    PostListResponse,
    PostRead,
    PostUpdate,
)


router = APIRouter(prefix='/posts', tags=['posts'], responses=error_responses(401, 403, 404))


# Swagger 문서에 응답 헤더 X-Cache를 설명한다.
CACHE_HEADER = {
    200: {
        'headers': {
            'X-Cache': {
                'description': 'HIT: 캐시에서 응답, MISS: DB에서 조회해 응답',
                'schema': {'type': 'string', 'enum': ['HIT', 'MISS']},
            }
        }
    }
}


# 글과 작성자를 가져옴 (없으면 404)
def _get_post_or_404(db: Session, post_id: int) -> Post:
    post = db.scalar(
        select(Post).options(joinedload(Post.author)).where(Post.id == post_id)
    )
    if post is None:
        raise NotFoundError('게시글을 찾을 수 없습니다.', code='POST_NOT_FOUND')
    return post



# 내 글 (글이 없으면 404, 내 글이 아니면 403)
def _get_owned_post(db: Session, post_id: int, user: User, action: str) -> Post:
    post = _get_post_or_404(db, post_id)
    if post.author_id != user.id:  # 작성자 검증(인가)
        raise ForbiddenError(f'작성자만 {action}할 수 있습니다.', code='NOT_POST_AUTHOR')
    return post


@router.post(
    '',
    response_model=PostRead,
    status_code=status.HTTP_201_CREATED,
    summary='글 작성(로그인 필요)',
)
def create_post(
    body: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    '''새 글을 작성합니다. 작성자는 요청 본문이 아니라 **로그인한 사용자**로 자동 지정됩니다.

    - 제목은 앞뒤 공백이 제거되며 1~200자, 본문은 1~10000자입니다.
    - 분류는 정해진 4가지(공지, 이벤트, 고객문의, 커뮤니티) 중 하나여야 합니다.
    '''
    post = Post(
        author_id=current_user.id,  # 작성자는 본문이 아니라 토큰에서 가져온다.
        category=body.category.value,
        title=body.title,
        content=body.content,
    )
    db.add(post)
    db.commit()
    post_cache.clear()  # 글이 바뀌었으니 목록·상세 캐시를 비운다.
    db.refresh(post)
    return post


@router.get(
    '',
    response_model=PostListResponse,
    summary='글 목록(최신순, 페이지네이션)',
    responses=CACHE_HEADER,
)
def list_posts(
    response: Response,
    page: int = Query(1, ge=1, description='페이지 번호(1부터)'),
    size: int = Query(10, ge=1, le=50, description='페이지당 글 수(최대 50)'),
    category: PostCategory | None = Query(None, description='분류로 거르기'),
    q: str | None = Query(None, min_length=1, max_length=50, description='제목·본문 검색어'),
    db: Session = Depends(get_db),
):
    '''글 목록을 **최신순**으로 돌려줍니다. 로그인 없이 볼 수 있습니다.

    - `page`, `size`(최대 50)로 쪽을 나눕니다.
    - `category`로 분류를 거르고, `q`로 제목·본문을 검색합니다(대소문자 무시).
    - 같은 조건의 조회는 30초 동안 캐시됩니다. 응답 헤더 `X-Cache`가 `HIT`면 캐시, `MISS`면 DB에서 조회한 결과입니다.
    '''
    # 같은 조건의 조회 결과가 캐시에 있으면 DB에 가지 않고 바로 돌려준다.
    cache_key = ('list', page, size, category.value if category else None, q)
    cached = post_cache.get(cache_key)
    if cached is not None:
        response.headers['X-Cache'] = 'HIT'
        return cached

    # 거르기 조건을 모은다. 조건이 없으면 전체가 대상이다.
    conditions = []
    if category is not None:
        conditions.append(Post.category == category.value)
    if q:
        conditions.append(
            or_(
                Post.title.icontains(q, autoescape=True),
                Post.content.icontains(q, autoescape=True),
            )
        )

    # 조건에 맞는 전체 글 수(페이지 계산용)
    total = db.scalar(select(func.count()).select_from(Post).where(*conditions))

    # 한 페이지 분량만 가져온다. joinedload로 작성자도 같은 쿼리에서 가져온다. (N+1 방지)
    posts = db.scalars(
        select(Post)
        .options(joinedload(Post.author))
        .where(*conditions)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    result = PostListResponse(
        items=[PostRead.model_validate(p) for p in posts],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,  # 올림 나눗셈
    )
    post_cache.set(cache_key, result)
    response.headers['X-Cache'] = 'MISS'
    return result


@router.get('/{post_id}', response_model=PostRead, summary='글 상세 조회', responses=CACHE_HEADER)
def read_post(post_id: int, response: Response, db: Session = Depends(get_db)):
    '''글 하나를 작성자 정보와 함께 돌려줍니다. 목록과 마찬가지로 30초 캐시되며 `X-Cache` 헤더로 확인할 수 있습니다.'''
    cache_key = ('detail', post_id)
    cached = post_cache.get(cache_key)
    if cached is not None:
        response.headers['X-Cache'] = 'HIT'
        return cached
    # 글이 없으면 404 오류가 나므로, 오류 응답은 캐시에 들어가지 않는다.
    result = PostRead.model_validate(_get_post_or_404(db, post_id))
    post_cache.set(cache_key, result)
    response.headers['X-Cache'] = 'MISS'
    return result


@router.patch('/{post_id}', response_model=PostRead, summary='글 수정(작성자만)')
def update_post(
    post_id: int,
    body: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    '''글을 수정합니다. **작성자만** 할 수 있습니다(아니면 `403`).

    - `PATCH`이므로 바꿀 항목만 보냅니다. 빈 본문이나 `null` 값은 `422`입니다.
    '''
    post = _get_owned_post(db, post_id, current_user, '수정')
    # 보낸 항목만 골라서 바꾼다(Enum은 문자열로 바뀐다).
    for field, value in body.model_dump(exclude_unset=True, mode='json').items():
        setattr(post, field, value)
    db.commit()
    post_cache.clear()
    db.refresh(post)
    return post


@router.delete('/{post_id}', status_code=status.HTTP_204_NO_CONTENT, summary='글 삭제(작성자만)')
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    '''글을 삭제합니다. **작성자만** 할 수 있습니다(아니면 `403`).

    - 그 글의 댓글은 함께 삭제되고, 첨부 이미지 파일도 지워집니다.
    - 성공하면 본문 없이 `204`를 돌려줍니다.
    '''
    post = _get_owned_post(db, post_id, current_user, '삭제')
    image_path = post.image_path  # 지운 뒤에는 읽을 수 없으니 미리 보관
    db.delete(post)  # 댓글은 DB의 CASCADE로 함께 지워진다.
    db.commit()
    post_cache.clear()
    delete_image(image_path)  # 이미지 파일도 함께 지운다.
