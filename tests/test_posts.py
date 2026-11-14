import time


def test_create_post(client, alice):
    r = client.post(
        '/posts',
        headers=alice,
        json={'category': '공지', 'title': '  제목  ', 'content': '본문'},
    )
    assert r.status_code == 201
    body = r.json()
    assert body['title'] == '제목'  # 앞뒤 공백 제거
    assert body['author']['username'] == 'alice'
    assert 'email' not in body['author']  # 작성자 이메일은 노출하지 않는다.


def test_create_requires_login(client):
    r = client.post('/posts', json={'category': '공지', 'title': 't', 'content': 'c'})
    assert r.status_code == 401


def test_create_validation(client, alice):
    bad_category = client.post('/posts', headers=alice, json={'category': '없는분류', 'title': 't', 'content': 'c'})
    blank_title = client.post('/posts', headers=alice, json={'category': '공지', 'title': '   ', 'content': 'c'})
    assert bad_category.status_code == 422
    assert blank_title.status_code == 422


def test_list_is_newest_first_with_pagination(client, alice, make_post):
    ids = [make_post(alice, title=f'글{i}')['id'] for i in range(5)]
    r = client.get('/posts')
    assert [p['id'] for p in r.json()['items']] == sorted(ids, reverse=True)
    assert r.json()['total'] == 5 and r.json()['pages'] == 1

    page2 = client.get('/posts', params={'size': 2, 'page': 2}).json()
    assert len(page2['items']) == 2 and page2['pages'] == 3
    page4 = client.get('/posts', params={'size': 2, 'page': 4}).json()
    assert page4['items'] == [] and page4['total'] == 5


def test_list_filters_and_search(client, alice, make_post):
    make_post(alice, title='점검 안내', category='점검')
    make_post(alice, title='이벤트 안내', category='이벤트')
    make_post(alice, title='Hello World', category='공지', content='plain')
    only_events = client.get('/posts', params={'category': '이벤트'}).json()
    assert only_events['total'] == 1
    assert client.get('/posts', params={'q': 'hello'}).json()['total'] == 1  # 대소문자 무시
    assert client.get('/posts', params={'q': '안내'}).json()['total'] == 2


def test_search_wildcards_are_escaped(client, alice, make_post):
    make_post(alice, title='abc')
    assert client.get('/posts', params={'q': 'a%c'}).json()['total'] == 0
    assert client.get('/posts', params={'q': 'a_c'}).json()['total'] == 0


def test_list_parameter_bounds(client):
    for params in ({'size': 0}, {'size': 51}, {'page': 0}, {'category': '없는분류'}):
        assert client.get('/posts', params=params).status_code == 422


def test_detail_and_not_found(client, alice, make_post):
    post = make_post(alice)
    assert client.get(f"/posts/{post['id']}").status_code == 200
    r = client.get('/posts/999999')
    assert r.status_code == 404
    assert r.json()['error']['code'] == 'POST_NOT_FOUND'


def test_patch_changes_only_sent_fields(client, alice, make_post):
    post = make_post(alice, title='원래 제목', content='원래 본문')
    time.sleep(1.1)  # SQLite 시각은 초 단위라서 updated_at이 달라지게 기다린다.
    r = client.patch(f"/posts/{post['id']}", headers=alice, json={'title': '새 제목'})
    assert r.status_code == 200
    assert r.json()['title'] == '새 제목'
    assert r.json()['content'] == '원래 본문'
    assert r.json()['updated_at'] > post['updated_at']


def test_patch_category(client, alice, make_post):
    post = make_post(alice)
    r = client.patch(f"/posts/{post['id']}", headers=alice, json={'category': '보안'})
    assert r.status_code == 200 and r.json()['category'] == '보안'


def test_patch_rejects_empty_and_null_and_invalid(client, alice, make_post):
    url = f"/posts/{make_post(alice)['id']}"
    assert client.patch(url, headers=alice, json={}).status_code == 422
    assert client.patch(url, headers=alice, json={'title': None}).status_code == 422
    assert client.patch(url, headers=alice, json={'category': '없음'}).status_code == 422


def test_only_author_can_patch_or_delete(client, alice, bob, make_post):
    post = make_post(alice)
    url = f"/posts/{post['id']}"
    r = client.patch(url, headers=bob, json={'title': '남이 수정'})
    assert r.status_code == 403
    assert r.json()['error']['code'] == 'NOT_POST_AUTHOR'
    assert client.delete(url, headers=bob).status_code == 403
    assert client.get(url).json()['title'] == post['title']  # 거절된 뒤에도 그대로


def test_unauthenticated_patch_and_delete(client, alice, make_post):
    url = f"/posts/{make_post(alice)['id']}"
    assert client.patch(url, json={'title': 'x'}).status_code == 401
    assert client.delete(url).status_code == 401


def test_delete_post(client, alice, make_post):
    url = f"/posts/{make_post(alice)['id']}"
    r = client.delete(url, headers=alice)
    assert r.status_code == 204 and r.content == b''
    assert client.get(url).status_code == 404
    assert client.delete(url, headers=alice).status_code == 404


def test_patch_and_delete_missing_post(client, alice):
    assert client.patch('/posts/999999', headers=alice, json={'title': 'x'}).status_code == 404
    assert client.delete('/posts/999999', headers=alice).status_code == 404
