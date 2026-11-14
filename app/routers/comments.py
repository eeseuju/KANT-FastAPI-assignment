from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.deps import get_current_user
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead


router = APIRouter(tags=['comments'])


def _post_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail='게시글을 찾을 수 없습니다.'
    )


# 글이 없으면 404 (본문까지 읽지 않도록 id만 조회)
def _ensure_post_exists(db: Session, post_id: int) -> None:
    if db.scalar(select(Post.id).where(Post.id == post_id)) is None:
        raise _post_not_found()


@router.post(
    '/posts/{post_id}/comments',
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary='댓글 작성(로그인 필요)',
)
def create_comment(
    post_id: int,
    body: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_post_exists(db, post_id)
    comment = Comment(
        post_id=post_id,
        author_id=current_user.id,  # 작성자는 본문이 아니라 토큰에서 가져온다
        content=body.content,
    )
    db.add(comment)
    try:
        db.commit()
    except IntegrityError:
        # 확인한 뒤 저장하기 전에 글이 지워진 경우(외래키가 거절)
        db.rollback()
        raise _post_not_found()
    db.refresh(comment)
    return comment


@router.get(
    '/posts/{post_id}/comments',
    response_model=list[CommentRead],
    summary='댓글 목록(오래된 순)',
)
def list_comments(
    post_id: int,
    page: int = Query(1, ge=1, description='페이지 번호(1부터)'),
    size: int = Query(20, ge=1, le=100, description='페이지당 댓글 수(최대 100)'),
    db: Session = Depends(get_db),
):
    _ensure_post_exists(db, post_id)
    # joinedload: 댓글과 작성자를 한 번의 쿼리로 가져온다(N+1 방지)
    return db.scalars(
        select(Comment)
        .options(joinedload(Comment.author))
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()


@router.delete(
    '/comments/{comment_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='댓글 삭제(작성자만)',
)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='댓글을 찾을 수 없습니다.'
        )
    if comment.author_id != current_user.id:  # 작성자 검증(인가)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail='작성자만 삭제할 수 있습니다.'
        )
    db.delete(comment)
    db.commit()