from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.core.errors import PayloadTooLargeError, UnsupportedMediaTypeError, error_responses
from app.core.storage import (
    MAX_IMAGE_BYTES,
    delete_image,
    detect_image_ext,
    save_image,
)
from app.db.session import get_db
from app.deps import get_current_user
from app.models.post import Post
from app.models.user import User
from app.routers.posts import _get_owned_post  # 같은 패키지의 글 조회·권한 확인을 재사용
from app.schemas.post import PostRead


router = APIRouter(tags=['uploads'], responses=error_responses(401, 403, 404, 413, 415))


# (스레드에서 실행) 파일을 저장하고 글의 image_path를 바꾼다.
def _attach_image(db: Session, post: Post, content: bytes, ext: str) -> Post:
    old_path = post.image_path
    new_path = save_image(content, ext)
    post.image_path = new_path
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_image(new_path)  # DB 저장에 실패하면 방금 저장한 파일도 되돌린다.
        raise
    db.refresh(post)
    post.author  # 응답을 만들 때 DB를 또 건드리지 않도록 미리 읽어 둔다.
    delete_image(old_path)  # 교체였다면 옛 이미지는 지운다.
    return post


@router.post(
    '/posts/{post_id}/image',
    response_model=PostRead,
    summary='글 이미지 업로드(작성자만, jpg/png/gif/webp, 최대 5MB)',
)
async def upload_post_image(
    post_id: int,
    file: UploadFile = File(description='이미지 파일(jpg, png, gif, webp / 최대 5MB)'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # DB 작업은 동기라서 스레드로 넘긴다. (서버가 다른 요청을 계속 받을 수 있게)
    post = await run_in_threadpool(_get_owned_post, db, post_id, current_user, '이미지 업로드')

    content = await file.read(MAX_IMAGE_BYTES + 1)  # 한도보다 1바이트 더 읽어서 초과를 알아낸다.
    if len(content) > MAX_IMAGE_BYTES:
        raise PayloadTooLargeError('이미지는 5MB 이하만 올릴 수 있습니다.', code='FILE_TOO_LARGE')
    ext = detect_image_ext(content)  # Content-Type이 아니라 파일 내용으로 확인한다.
    if ext is None:
        raise UnsupportedMediaTypeError('jpg, png, gif, webp 이미지만 올릴 수 있습니다.', code='UNSUPPORTED_FILE_TYPE')
    return await run_in_threadpool(_attach_image, db, post, content, ext)