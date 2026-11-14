import pytest
from fastapi.testclient import TestClient

from app.main import app


def assert_error_shape(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {'error'}
    assert set(body['error']) == {'code', 'message', 'details'}
    assert body['error']['code'] == code


def test_unknown_path(client):
    r = client.get('/no-such-path')
    assert_error_shape(r, 404, 'NOT_FOUND')
    assert r.json()['error']['message'] == '요청한 주소를 찾을 수 없습니다.'


def test_method_not_allowed(client):
    assert_error_shape(client.delete('/health'), 405, 'METHOD_NOT_ALLOWED')


def test_missing_token_is_unified_and_korean(client):
    r = client.get('/users/me')
    assert_error_shape(r, 401, 'UNAUTHORIZED')
    assert r.json()['error']['message'] == '로그인이 필요합니다.'
    assert r.headers['www-authenticate'] == 'Bearer'


def test_validation_error_lists_fields_and_hides_input(client):
    r = client.post('/auth/signup', json={'email': 'x', 'username': 'a', 'password': 'sh0rt'})
    assert_error_shape(r, 422, 'VALIDATION_ERROR')
    assert all({'field', 'message'} == set(d) for d in r.json()['error']['details'])
    assert 'sh0rt' not in r.text


def test_query_validation_field_name(client):
    r = client.get('/posts', params={'size': 0})
    assert_error_shape(r, 422, 'VALIDATION_ERROR')
    assert r.json()['error']['details'][0]['field'] == 'query.size'


def test_malformed_json_body(client):
    r = client.post('/auth/signup', content=b'{not json', headers={'Content-Type': 'application/json'})
    assert_error_shape(r, 422, 'VALIDATION_ERROR')


def test_unexpected_error_is_hidden_behind_generic_500(client):
    def boom():
        raise RuntimeError('internal secret: db password=hunter2')

    app.add_api_route('/_boom_for_test', boom, include_in_schema=False)
    try:
        with TestClient(app, raise_server_exceptions=False) as safe_client:
            r = safe_client.get('/_boom_for_test')
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, 'path', '') != '/_boom_for_test']
    assert_error_shape(r, 500, 'INTERNAL_ERROR')
    assert 'hunter2' not in r.text and 'RuntimeError' not in r.text