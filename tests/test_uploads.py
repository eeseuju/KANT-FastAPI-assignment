import os
import re


from app.core.storage import MAX_IMAGE_BYTES


PNG = b'\x89PNG\r\n\x1a\n' + os.urandom(64)
JPG = b'\xff\xd8\xff\xe0' + os.urandom(64)
GIF = b'GIF89a' + os.urandom(64)
WEBP = b'RIFF' + b'\x10\x00\x00\x00' + b'WEBP' + os.urandom(32)


def upload(client, post_id, headers, content=PNG, name='photo.png', ctype='image/png'):
    return client.post(
        f'/posts/{post_id}/image', headers=headers, files={'file': (name, content, ctype)}
    )


def test_upload_requires_login_and_author(client, alice, bob, make_post, tmp_path):
    post = make_post(alice)
    assert upload(client, post['id'], {}).status_code == 401
    r = upload(client, post['id'], bob)
    assert r.status_code == 403
    assert list(tmp_path.iterdir()) == []  # 거절된 업로드는 파일을 남기지 않는다.


def test_upload_missing_post(client, alice):
    assert upload(client, 999999, alice).status_code == 404


def test_valid_image_is_saved_with_random_name(client, alice, make_post, tmp_path):
    post = make_post(alice)
    r = upload(client, post['id'], alice, name='../../evil name.png')
    assert r.status_code == 200
    path = r.json()['image_path']
    assert re.fullmatch(r'/uploads/[0-9a-f]{32}\.png', path)  # 사용자가 보낸 파일명은 쓰지 않는다.
    saved = list(tmp_path.iterdir())
    assert [p.name for p in saved] == [path.split('/')[-1]]
    assert saved[0].read_bytes() == PNG


def test_fake_images_are_rejected(client, alice, make_post, tmp_path):
    post = make_post(alice)
    for content in (b'plain text', b'', b'<html><script>alert(1)</script></html>'):
        r = upload(client, post['id'], alice, content=content, name='fake.png')
        assert r.status_code == 415
        assert r.json()['error']['code'] == 'UNSUPPORTED_FILE_TYPE'
    assert list(tmp_path.iterdir()) == []
    assert client.get(f"/posts/{post['id']}").json()['image_path'] is None


def test_too_large_is_rejected(client, alice, make_post, tmp_path):
    post = make_post(alice)
    r = upload(client, post['id'], alice, content=PNG + b'x' * MAX_IMAGE_BYTES)
    assert r.status_code == 413
    assert r.json()['error']['code'] == 'FILE_TOO_LARGE'
    assert list(tmp_path.iterdir()) == []


def test_content_decides_type_not_content_type_header(client, alice, make_post):
    post = make_post(alice)
    r = upload(client, post['id'], alice, content=JPG, name='a.txt', ctype='text/plain')
    assert r.status_code == 200
    assert r.json()['image_path'].endswith('.jpg')


def test_replacing_removes_the_old_file(client, alice, make_post, tmp_path):
    post = make_post(alice)
    first = upload(client, post['id'], alice, content=PNG).json()['image_path']
    second = upload(client, post['id'], alice, content=GIF).json()['image_path']
    third = upload(client, post['id'], alice, content=WEBP).json()['image_path']
    assert len({first, second, third}) == 3
    assert [p.name for p in tmp_path.iterdir()] == [third.split('/')[-1]]  # 마지막 파일만 남는다.
    assert third.endswith('.webp')


def test_image_survives_patch_and_is_removed_with_post(client, alice, make_post, tmp_path):
    post = make_post(alice)
    path = upload(client, post['id'], alice).json()['image_path']
    patched = client.patch(f"/posts/{post['id']}", headers=alice, json={'title': '수정'})
    assert patched.json()['image_path'] == path
    assert client.delete(f"/posts/{post['id']}", headers=alice).status_code == 204
    assert list(tmp_path.iterdir()) == []  # 글을 지우면 이미지 파일도 지워진다.