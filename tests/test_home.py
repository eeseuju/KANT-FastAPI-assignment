import re

from app.main import app


def test_home_page_is_html_with_links(client):
    r = client.get('/')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/html')
    assert 'Board API' in r.text
    for link in ('/docs', '/redoc', '/health'):
        assert f'href="{link}"' in r.text  # 문서·상태 확인으로 가는 버튼


def test_home_page_loads_no_external_resources(client):
    # 외부 CSS·JS·이미지·글꼴을 불러오지 않는다. 바깥으로 나가는 주소가 하나도 없어야 한다.
    urls = re.findall(r'https?://[^\s"\'<>]+', client.get('/').text)
    assert urls == []


def test_home_page_is_not_listed_in_openapi():
    assert '/' not in app.openapi()['paths']  # 문서에는 API만 나온다
