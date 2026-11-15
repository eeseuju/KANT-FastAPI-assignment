import pytest

from app.main import app

HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete'}


@pytest.fixture(scope='module')
def spec():
    return app.openapi()


def operations(spec):
    for path, item in spec['paths'].items():
        for method, op in item.items():
            if method in HTTP_METHODS:
                yield path, method, op


def test_docs_pages_are_served(client):
    docs = client.get('/docs')
    assert docs.status_code == 200 and 'swagger' in docs.text.lower()
    assert client.get('/redoc').status_code == 200
    assert client.get('/openapi.json').status_code == 200


def test_api_description_explains_how_to_use_it(spec):
    info = spec['info']
    assert info['title'] and info['version']
    assert 'Authorize' in info['description']  # 사용 방법 안내
    assert 'error' in info['description']  # 오류 형식 안내


def test_all_expected_endpoints_exist(spec):
    found = {(m, p) for p, m, _ in operations(spec)}
    expected = {
        ('get', '/health'),
        ('post', '/auth/signup'),
        ('post', '/auth/login'),
        ('get', '/users/me'),
        ('post', '/posts'),
        ('get', '/posts'),
        ('get', '/posts/{post_id}'),
        ('patch', '/posts/{post_id}'),
        ('delete', '/posts/{post_id}'),
        ('post', '/posts/{post_id}/comments'),
        ('get', '/posts/{post_id}/comments'),
        ('delete', '/comments/{comment_id}'),
        ('post', '/posts/{post_id}/image'),
    }
    assert expected <= found


def test_tags_are_declared_with_descriptions_in_order(spec):
    declared = [t['name'] for t in spec['tags']]
    assert declared == ['auth', 'users', 'posts', 'comments', 'uploads', 'health']
    assert all(t['description'] for t in spec['tags'])
    used = {tag for _, _, op in operations(spec) for tag in op['tags']}
    assert used <= set(declared)


def test_every_endpoint_has_summary_description_and_tag(spec):
    for path, method, op in operations(spec):
        where = f'{method.upper()} {path}'
        summary = op.get('summary', '')
        # summary를 안 쓰면 FastAPI가 함수 이름으로 영어 요약을 자동으로 만들어 준다.
        # 그걸 걸러내려고 "한글 요약"인지 확인한다.
        assert any('가' <= ch <= '힣' for ch in summary), f'{where}: 한글 요약(summary)이 없음 (지금 값: {summary!r})'
        assert op.get('description'), f'{where}: description 없음(함수에 독스트링을 쓴다)'
        assert op.get('tags'), f'{where}: tag 없음'


def test_protected_endpoints_document_401_and_lock(spec):
    protected = [
        ('get', '/users/me'), ('post', '/posts'), ('patch', '/posts/{post_id}'),
        ('delete', '/posts/{post_id}'), ('post', '/posts/{post_id}/comments'),
        ('delete', '/comments/{comment_id}'), ('post', '/posts/{post_id}/image'),
    ]
    for path, method, op in operations(spec):
        if (method, path) in protected:
            assert op.get('security'), f'{method.upper()} {path}: 자물쇠(security) 없음'
            assert '401' in op['responses']


def test_endpoints_with_path_ids_document_404(spec):
    for path, method, op in operations(spec):
        if '{' in path:
            assert '404' in op['responses'], f'{method.upper()} {path}: 404 문서 없음'


def test_author_only_endpoints_document_403(spec):
    for path, method in (('/posts/{post_id}', 'patch'), ('/posts/{post_id}', 'delete'),
                         ('/comments/{comment_id}', 'delete'), ('/posts/{post_id}/image', 'post')):
        assert '403' in spec['paths'][path][method]['responses']


def test_error_schema_is_documented_with_examples(spec):
    schemas = spec['components']['schemas']
    assert {'ErrorResponse', 'ErrorBody', 'ErrorDetail'} <= set(schemas)
    assert 'HTTPValidationError' not in schemas  # 422도 우리 오류 형식으로 문서화됨
    assert schemas['ErrorResponse'].get('examples')
    ref = spec['paths']['/posts/{post_id}']['patch']['responses']['422']['content']['application/json']['schema']['$ref']
    assert ref.endswith('/ErrorResponse')


def test_cache_header_is_documented(spec):
    for path in ('/posts', '/posts/{post_id}'):
        headers = spec['paths'][path]['get']['responses']['200'].get('headers', {})
        assert 'X-Cache' in headers


def test_upload_and_conflict_errors_are_documented(spec):
    upload = spec['paths']['/posts/{post_id}/image']['post']['responses']
    assert {'413', '415'} <= set(upload)
    assert '409' in spec['paths']['/auth/signup']['post']['responses']
    assert '503' in spec['paths']['/health']['get']['responses']


def test_post_categories_are_documented_as_exactly_four_values(spec):
    # Swagger의 드롭다운에 허용 값이 정확히 이 4가지만 나온다.
    assert spec['components']['schemas']['PostCategory']['enum'] == ['공지', '이벤트', '고객문의', '커뮤니티']


def test_request_body_fields_have_descriptions(spec):
    schemas = spec['components']['schemas']
    for name in ('UserCreate', 'PostCreate', 'PostUpdate', 'CommentCreate'):
        for field, prop in schemas[name]['properties'].items():
            assert prop.get('description'), f'{name}.{field}: 설명 없음'