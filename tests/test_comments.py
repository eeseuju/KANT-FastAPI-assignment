from sqlalchemy import func, select

from app.models.comment import Comment


def add_comment(client, post_id, headers, content='댓글'):
    return client.post(f'/posts/{post_id}/comments', headers=headers, json={'content': content})


def test_create_comment(client, alice, make_post):
    post = make_post(alice)
    r = add_comment(client, post['id'], alice, '첫 댓글')
    assert r.status_code == 201
    body = r.json()
    assert body['post_id'] == post['id']
    assert set(body['author']) == {'id', 'username'}  # 작성자 이메일은 노출하지 않는다.


def test_create_requires_login(client, alice, make_post):
    post = make_post(alice)
    assert client.post(f"/posts/{post['id']}/comments", json={'content': 'x'}).status_code == 401


def test_comment_on_missing_post_is_404(client, alice):
    assert add_comment(client, 999999, alice).status_code == 404
    assert client.get('/posts/999999/comments').status_code == 404


def test_content_validation(client, alice, make_post):
    post = make_post(alice)
    assert add_comment(client, post['id'], alice, '   ').status_code == 422
    assert add_comment(client, post['id'], alice, 'x' * 1001).status_code == 422


def test_list_is_oldest_first_with_pagination(client, alice, bob, make_post):
    post = make_post(alice)
    for text, who in (('첫 댓글', alice), ('두번째', bob), ('세번째', bob)):
        add_comment(client, post['id'], who, text)
    url = f"/posts/{post['id']}/comments"
    assert [c['content'] for c in client.get(url).json()] == ['첫 댓글', '두번째', '세번째']
    assert [c['content'] for c in client.get(url, params={'size': 2, 'page': 2}).json()] == ['세번째']
    assert client.get(url, params={'size': 0}).status_code == 422


def test_only_comment_author_can_delete(client, alice, bob, make_post):
    post = make_post(alice)
    comment = add_comment(client, post['id'], bob).json()
    url = f"/comments/{comment['id']}"
    assert client.delete(url).status_code == 401
    assert client.delete(url, headers=alice).status_code == 403  # 글 작성자도 남의 댓글은 지울 수 없다.
    r = client.delete(url, headers=bob)
    assert r.status_code == 204 and r.content == b''
    again = client.delete(url, headers=bob)
    assert again.status_code == 404
    assert again.json()['error']['code'] == 'COMMENT_NOT_FOUND'


def test_deleting_a_post_removes_its_comments(client, session_factory, alice, bob, make_post):
    post = make_post(alice)
    add_comment(client, post['id'], alice)
    add_comment(client, post['id'], bob)
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Comment)) == 2
    assert client.delete(f"/posts/{post['id']}", headers=alice).status_code == 204
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Comment)) == 0  # CASCADE
    assert client.get(f"/posts/{post['id']}/comments").status_code == 404