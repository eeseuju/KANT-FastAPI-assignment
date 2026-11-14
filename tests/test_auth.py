from sqlalchemy import select

from app.core.security import create_access_token
from app.models.user import User


PASSWORD = 'password1234'


def signup(client, email='a@example.com', username='alice', password=PASSWORD):
    return client.post(
        '/auth/signup', json={'email': email, 'username': username, 'password': password}
    )


def test_signup_success_hides_password(client):
    r = signup(client)
    assert r.status_code == 201
    body = r.json()
    assert body['email'] == 'a@example.com'
    assert 'password' not in body and 'hashed_password' not in body


def test_password_is_stored_hashed(client, session_factory):
    signup(client)
    with session_factory() as db:
        user = db.scalar(select(User))
    assert user.hashed_password != PASSWORD
    assert user.hashed_password.startswith('$2b$')


def test_duplicate_email_and_username_are_409(client):
    signup(client)
    assert signup(client, username='other').status_code == 409  # 같은 이메일
    assert signup(client, email='b@example.com').status_code == 409  # 같은 닉네임
    r = signup(client, email='b@example.com')
    assert r.json()['error']['code'] == 'USER_ALREADY_EXISTS'


def test_email_is_case_insensitive(client):
    signup(client, email='A@Example.com')
    assert signup(client, email='a@example.com', username='second').status_code == 409


def test_signup_validation_errors(client):
    r = client.post(
        '/auth/signup', json={'email': 'not-an-email', 'username': 'a', 'password': 'sh0rt'}
    )
    assert r.status_code == 422
    fields = {d['field'] for d in r.json()['error']['details']}
    assert {'body.email', 'body.username', 'body.password'} <= fields
    assert 'sh0rt' not in r.text  # 입력한 비밀번호를 응답에 되돌려 주지 않는다.


def test_password_over_72_bytes_is_rejected(client):
    r = signup(client, password='ㄱ' * 25)  # 25글자지만 75바이트
    assert r.status_code == 422
    assert '72바이트' in r.text


def test_login_success_returns_bearer_token(client):
    signup(client)
    r = client.post('/auth/login', data={'username': 'a@example.com', 'password': PASSWORD})
    assert r.status_code == 200
    assert r.json()['token_type'] == 'bearer'
    assert r.json()['access_token']


def test_login_failure_message_is_same_for_wrong_password_and_unknown_email(client):
    signup(client)
    wrong_pw = client.post('/auth/login', data={'username': 'a@example.com', 'password': 'wrong-password'})
    no_user = client.post('/auth/login', data={'username': 'nobody@example.com', 'password': PASSWORD})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()  # 어느 쪽이 틀렸는지 알려 주지 않는다.
    assert wrong_pw.headers['www-authenticate'] == 'Bearer'


def test_me_requires_token(client):
    r = client.get('/users/me')
    assert r.status_code == 401
    assert r.json()['error']['code'] == 'UNAUTHORIZED'


def test_me_returns_own_profile(client, alice):
    r = client.get('/users/me', headers=alice)
    assert r.status_code == 200
    assert r.json()['username'] == 'alice'


def test_expired_token(client, alice):
    token = create_access_token(1, expires_minutes=-1)
    r = client.get('/users/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 401
    assert r.json()['error']['code'] == 'TOKEN_EXPIRED'


def test_tampered_token(client, alice):
    token = alice['Authorization'].split()[1]
    broken = token[:-3] + ('abc' if not token.endswith('abc') else 'xyz')
    r = client.get('/users/me', headers={'Authorization': f'Bearer {broken}'})
    assert r.status_code == 401
    assert r.json()['error']['code'] == 'INVALID_TOKEN'


def test_token_of_nonexistent_user(client):
    token = create_access_token(999999)  # 서명은 맞지만 그런 사용자는 없다.
    r = client.get('/users/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 401
    assert r.json()['error']['code'] == 'INVALID_TOKEN'