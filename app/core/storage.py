import uuid
from pathlib import Path


# 경로: root/uploads (app/core/storage.py 기준으로 두 단계 위가 루트)
UPLOAD_DIR = Path(__file__).resolve().parents[2] / 'uploads'
UPLOAD_URL_PREFIX = '/uploads'
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB


# 파일 맨 앞 바이트로 이미지 확인 후 확장자 반환
def detect_image_ext(content: bytes) -> str | None:
    if content.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if content.startswith((b'GIF87a', b'GIF89a')):
        return '.gif'
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return '.webp'
    return None


# 서버가 정한 이름 저장 및 반환
def save_image(content: bytes, ext: str) -> str:
    UPLOAD_DIR.mkdir(exist_ok=True)
    name = f'{uuid.uuid4().hex}{ext}'  # 사용자가 보낸 파일 이름은 쓰지 않는다.
    (UPLOAD_DIR / name).write_bytes(content)
    return f'{UPLOAD_URL_PREFIX}/{name}'


# 저장된 이미지 삭제
def delete_image(image_path: str | None) -> None:
    if not image_path:
        return
    # .name: 폴더 부분을 버리고 파일 이름만 쓴다. (../ 같은 경로 조작 방지)
    (UPLOAD_DIR / Path(image_path).name).unlink(missing_ok=True)