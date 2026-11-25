import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect

from hosting_support import PAGES

pytestmark = pytest.mark.browser


@pytest.fixture
def hosted_page(page, site_url, awake):
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(30000)
    problems = []
    page.on('pageerror', lambda error: problems.append(str(error)))

    def check_request(request):
        target = urlsplit(request.url)
        if target.scheme == 'http' or target.hostname in ('localhost', '127.0.0.1', '::1'):
            problems.append('Insecure or local resource: ' + target.path)

    def check_response(response):
        target = urlsplit(response.url)
        if target.netloc != urlsplit(site_url).netloc:
            return
        if response.status >= 500 or (target.path.startswith(('/css/', '/js/', '/img/', '/static/')) and response.status >= 400):
            problems.append(f'HTTP {response.status}: {target.path}')

    def check_failure(request):
        target = urlsplit(request.url)
        # Page navigation can cancel pending fetches/resources. Chromium and
        # Firefox use different names for this normal cancellation.
        cancelled = request.failure in ('net::ERR_ABORTED', 'NS_BINDING_ABORTED')
        if target.netloc == urlsplit(site_url).netloc and not cancelled:
            problems.append(f'Failed request: {target.path} ({request.failure})')

    page.on('request', check_request)
    page.on('response', check_response)
    page.on('requestfailed', check_failure)
    yield page
    assert not problems, '\n'.join(problems)


@pytest.mark.parametrize('path', PAGES)
def test_pages_in_real_browser(hosted_page, site_url, path):
    response = hosted_page.goto(site_url + path, wait_until='load')
    assert response.status == 200
    expect(hosted_page.locator('main')).to_be_visible()
    assert hosted_page.title()
    assert hosted_page.evaluate('Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)')
    if path == '/tickets.html':
        expect(hosted_page.locator('#products-body')).not_to_have_attribute('aria-busy', 'true')
        expect(hosted_page.locator('#products-body')).not_to_contain_text('Не удалось')
        expect(hosted_page.locator('#products-body tr').first).to_be_visible()


@pytest.mark.parametrize('width', [360, 768, 1440])
@pytest.mark.parametrize('path', ['/', '/tickets.html', '/cart.html', '/privacy.html'])
def test_hosted_responsive_layout(hosted_page, site_url, browser_name, path, width):
    hosted_page.set_viewport_size({'width': width, 'height': 1000})
    hosted_page.goto(site_url + path, wait_until='load')
    hosted_page.evaluate('document.fonts.ready')
    if path == '/tickets.html':
        expect(hosted_page.locator('#products-body')).not_to_have_attribute('aria-busy', 'true')
    overflow = hosted_page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
    directory = Path('artifacts/hosting/layouts') / browser_name
    directory.mkdir(parents=True, exist_ok=True)
    hosted_page.screenshot(path=str(directory / f'{path.strip("/") or "index"}-{width}.png'), full_page=True)
    assert not overflow, f'Horizontal overflow on {path} at {width}px'


def test_homepage_load_budget(hosted_page, site_url, pytestconfig, record_property):
    # The session fixture woke the service; report warm browser load separately.
    hosted_page.goto(site_url + '/', wait_until='load')
    hosted_page.wait_for_function('performance.getEntriesByType("navigation")[0].loadEventEnd > 0')
    seconds = hosted_page.evaluate('performance.getEntriesByType("navigation")[0].loadEventEnd / 1000')
    record_property('homepage_load_seconds', round(seconds, 3))
    assert seconds <= pytestconfig.getoption('--hosting-load-seconds'), f'Homepage load took {seconds:.2f}s'


def test_native_registration_validation_and_policy_links(hosted_page, site_url):
    hosted_page.goto(site_url + '/tickets.html')
    form = hosted_page.locator('#register')
    assert not form.evaluate('(form) => form.checkValidity()')
    hosted_page.locator('#reg-email').fill('invalid-email')
    assert not hosted_page.locator('#reg-email').evaluate('(input) => input.checkValidity()')
    for name in ('terms', 'privacy'):
        checkbox = hosted_page.locator('#reg-' + name)
        assert checkbox.get_attribute('required') is not None
        link = hosted_page.locator(f'label[for="reg-{name}"] a')
        with hosted_page.expect_popup() as opened:
            link.click()
        popup = opened.value
        popup.wait_for_load_state()
        assert popup.url == site_url + '/' + name + '.html'
        popup.close()
    expect(hosted_page.locator('#reg-email')).to_have_value('invalid-email')


def test_basic_accessibility_and_keyboard(hosted_page, site_url):
    hosted_page.goto(site_url + '/tickets.html')
    assert hosted_page.locator('img:not([alt])').count() == 0
    assert hosted_page.locator('html').get_attribute('lang') == 'ru'
    missing_labels = hosted_page.evaluate('''() => Array.from(document.querySelectorAll('input:not([type=hidden]),textarea,select'))
        .filter(e => !e.labels?.length && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby')).map(e => e.id)''')
    assert not missing_labels, 'Unlabelled fields: ' + ', '.join(missing_labels)
    hosted_page.locator('#reg-email').focus()
    hosted_page.keyboard.press('Tab')
    expect(hosted_page.locator('#reg-phone')).to_be_focused()
    focus_visible = hosted_page.locator('#reg-phone').evaluate('''e => {
        const s = getComputedStyle(e); return (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none';
    }''')
    assert focus_visible, 'Keyboard focus must be visible'


def test_admin_login_with_hosting_credentials(hosted_page, site_url):
    email = os.environ.get('HOSTING_ADMIN_EMAIL')
    password = os.environ.get('HOSTING_ADMIN_PASSWORD')
    if not email or not password:
        pytest.skip('Set HOSTING_ADMIN_EMAIL and HOSTING_ADMIN_PASSWORD for admin login check')
    hosted_page.goto(site_url + '/admin/login/')
    hosted_page.locator('#id_username').fill(email)
    hosted_page.locator('#id_password').fill(password)
    hosted_page.locator('input[type=submit]').click()
    expect(hosted_page).to_have_url(site_url + '/admin/')
    response = hosted_page.goto(site_url + '/admin/main/product/add/')
    assert response.status == 200
    expect(hosted_page.locator('#id_name')).to_be_visible()
    # No product is saved; context teardown discards local cookies.
