import socket
import ssl
import time
from urllib.parse import urldefrag, urljoin, urlsplit

import pytest

from hosting_support import Document, PAGES


def test_dns_and_verified_tls_certificate(site_url):
    target = urlsplit(site_url)
    port = target.port or 443
    assert socket.getaddrinfo(target.hostname, port, type=socket.SOCK_STREAM)
    with socket.create_connection((target.hostname, port), timeout=20) as raw:
        with ssl.create_default_context().wrap_socket(raw, server_hostname=target.hostname) as tls:
            cert = tls.getpeercert()  # Validates issuer, dates and hostname, never disables TLS verification.
            assert ssl.cert_time_to_seconds(cert['notAfter']) - time.time() > 7 * 86400, 'Certificate expires in less than 7 days'
            assert tls.version() in ('TLSv1.2', 'TLSv1.3')


def test_http_redirects_to_https(site, site_url):
    response = site.request(site_url.replace('https://', 'http://', 1) + '/', follow=False)
    assert response.status in (301, 302, 307, 308), 'HTTP must redirect to HTTPS'
    assert urljoin(response.url, response.headers.get('Location', '')) == site_url + '/'


@pytest.mark.parametrize('path', PAGES)
def test_public_page_available(public_pages, path):
    response = public_pages[path]
    assert response.status == 200, f'{path}: HTTP {response.status}'
    assert 'text/html' in response.headers.get('Content-Type', '')
    assert '<html' in response.text.lower()
    assert 'DisallowedHost' not in response.text


def test_at_least_ten_internal_links_and_fragments(site, site_url, public_pages):
    links = set()
    for path, response in public_pages.items():
        for href in Document(response.text).links:
            target = urljoin(site_url + path, href)
            if href != '#' and urlsplit(target).netloc == urlsplit(site_url).netloc:
                links.add(target)
    assert len(links) >= 10, 'Fewer than 10 distinct internal links available for checking'
    cache = {site_url + path: response for path, response in public_pages.items()}
    for target in sorted(links):
        url, fragment = urldefrag(target)
        if url not in cache:
            cache[url] = site.request(url)
        response = cache[url]
        assert response.status == 200, f'Broken link: {target} (HTTP {response.status})'
        if fragment:
            assert fragment in Document(response.text).ids, f'Missing fragment: {target}'


def test_public_assets_and_admin_styles(site, site_url, public_pages):
    admin = site.request('/admin/login/')
    assert admin.status == 200
    assets = set()
    for path, response in [*public_pages.items(), ('/admin/login/', admin)]:
        assets.update(urljoin(site_url + path, src) for src in Document(response.text).assets)
    assert any('/static/admin/' in asset for asset in assets), 'Admin styles missing'
    assert any('/js/' in asset for asset in assets) and any('/css/' in asset for asset in assets)
    for url in sorted(assets):
        assert not url.startswith('http://'), 'Mixed content asset found'
        if urlsplit(url).netloc != urlsplit(site_url).netloc:
            continue
        response = site.request(url)
        assert response.status == 200, f'Asset failed: {url} (HTTP {response.status})'
        assert response.body, f'Empty asset: {url}'
        mime = response.headers.get('Content-Type', '').lower()
        if urlsplit(url).path.endswith('.css'):
            assert 'text/css' in mime, f'Wrong CSS content type: {url}'
        elif urlsplit(url).path.endswith('.js'):
            assert 'javascript' in mime, f'Wrong JS content type: {url}'
        elif '/img/' in urlsplit(url).path:
            assert mime.startswith('image/'), f'Wrong image content type: {url}'


def test_backend_database_health(site):
    response = site.request('/api/health')
    assert response.status == 200
    assert response.json() == {'status': 'ok'}


def test_catalogue_is_json_and_sorted(site):
    response = site.request('/api/products?sort=price')
    assert response.status == 200
    items = response.json()['items']
    assert isinstance(items, list)
    assert all({'id', 'name', 'available', 'price', 'unit_price'} <= row.keys() for row in items)
    assert [row['price'] for row in items] == sorted(row['price'] for row in items)


def test_all_permanent_artist_tickets_have_schedule_and_images(site):
    response = site.request('/api/products')
    assert response.status == 200
    items = {item['alias']: item for item in response.json()['items']}
    expected = {
        'shaman-standard': ('Шаман', 'img/ticket-dance-floor.png'),
        'shaman-vip': ('Шаман', 'img/ticket-vip-zone.png'),
        'vanya-standard': ('Ваня Дмитриенко', 'img/ticket-dance-floor.png'),
        'vanya-vip': ('Ваня Дмитриенко', 'img/ticket-vip-zone.png'),
        'stas-standard': ('Стас Михайлов', 'img/ticket-dance-floor.png'),
        'stas-vip': ('Стас Михайлов', 'img/ticket-vip-zone.png'),
        'anna-standard': ('Анна Асти', 'img/ticket-dance-floor.png'),
        'anna-vip': ('Анна Асти', 'img/ticket-vip-zone.png'),
    }
    assert set(expected) <= set(items), 'Published catalogue is missing permanent tickets'

    for alias, (artist, image) in expected.items():
        ticket = items[alias]
        assert ticket['available']
        assert ticket['image'] == image
        assert len(ticket['categories']) == 1
        category = ticket['categories'][0]
        assert category['name'] == artist
        assert category['performance_date'] == '2027-07-16'
        assert category['performance_time']
        assert 'performance_price' not in category
        image_response = site.request('/' + image)
        assert image_response.status == 200
        assert image_response.headers.get('Content-Type', '').startswith('image/')


def test_search_and_policy_download(site):
    response = site.request('/api/search?q=hosting-check-no-match-9172')
    assert response.status == 200 and isinstance(response.json()['items'], list)
    policy = site.request('/api/privacy/download')
    assert policy.status == 200 and len(policy.body) > 100
    assert 'text/plain' in policy.headers.get('Content-Type', '')
    assert 'attachment' in policy.headers.get('Content-Disposition', '')


@pytest.mark.parametrize('path', ['/api/profile', '/api/cart', '/api/orders', '/api/actions', '/api/feedback'])
def test_guest_cannot_read_private_data(site, path):
    response = site.request(path)
    assert response.status == 401
    assert 'error' in response.json()


def test_account_and_admin_require_login(site):
    for path, destination in [('/account.html', '/tickets.html#login'), ('/admin/', '/admin/login/')]:
        response = site.request(path, follow=False)
        assert response.status == 302
        assert response.headers.get('Location', '').startswith(destination)


@pytest.mark.parametrize('path', ['/api/register', '/api/login', '/api/feedback'])
def test_csrf_rejects_missing_token(site, path):
    # Empty body cannot create data even if CSRF is accidentally disabled.
    assert site.request(path, method='POST', data={}).status == 403


@pytest.mark.parametrize('path', ['/api/register', '/api/login', '/api/feedback'])
def test_valid_origin_reaches_form_validation(site, path):
    site.request('/tickets.html')
    response = site.request(path, method='POST', data={}, csrf=True)
    assert response.status == 400, f'{path}: expected form validation, got HTTP {response.status}'
    assert response.json()['errors']
    foreign = site.request(path, method='POST', data={}, csrf=True, headers={'Origin': 'https://untrusted.example'})
    assert foreign.status == 403


def test_secure_csrf_cookie_and_headers(site):
    response = site.request('/tickets.html')
    cookie = site.cookie('csrftoken')
    secure = cookie is not None and cookie.secure
    assert secure, 'Set DJANGO_COOKIE_SECURE=true on HTTPS hosting'
    assert cookie.get_nonstandard_attr('SameSite', '').lower() in ('lax', 'strict')
    assert response.headers.get('X-Content-Type-Options', '').lower() == 'nosniff'
    assert response.headers.get('X-Frame-Options', '').upper() in ('DENY', 'SAMEORIGIN')


def test_missing_page_has_no_django_debug_details(site):
    response = site.request('/hosting-check-nonexistent-page-9172/')
    assert response.status == 404
    assert not any(marker in response.text for marker in (
        'DEBUG = True', 'Django tried these URL patterns', 'Using the URLconf defined',
        'Traceback', 'Request Method:', 'Exception Location:',
    )), 'Public error page exposes Django debug details; configure production error pages'


@pytest.mark.parametrize('path', ['/.env', '/.git/config', '/compose.yaml', '/db.sqlite3', '/zvukfest/settings.py'])
def test_private_files_not_published(site, path):
    response = site.request(path, follow=False)
    # Never include response contents in an assertion/report: it could be a leaked secret.
    assert response.status in (403, 404), f'Private path is not blocked: {path}, HTTP {response.status}'
