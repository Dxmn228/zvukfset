import os
from urllib.parse import urlsplit

import pytest

from hosting_support import PAGES, Site, wait_until_ready
from hosting_accounts import new_account, registration, record_account
from hosting_browser import hosted_page  # Shared real-browser fixture for both UI modules.


def pytest_addoption(parser):
    group = parser.getgroup('hosting')
    group.addoption('--hosting-url', default=os.environ.get('HOSTING_BASE_URL', 'https://zvukfest.de3.netrun.io'))
    group.addoption('--hosting-browser', action='store_true', help='Run real browser checks')
    group.addoption('--hosting-writes', action='store_true', help='Create a labelled demo user, feedback and order')
    group.addoption('--hosting-load-seconds', type=float, default=3.0, help='Homepage warm load budget from lab 4')


def pytest_collection_modifyitems(config, items):
    for item in items:
        for marker in ('browser', 'writes'):
            if marker in item.keywords and not config.getoption('--hosting-' + marker):
                item.add_marker(pytest.mark.skip(reason='Enable --hosting-' + marker))


@pytest.fixture(scope='session')
def site_url(pytestconfig):
    value = pytestconfig.getoption('--hosting-url')
    if not value:
        raise pytest.UsageError('Specify --hosting-url=https://zvukfest.de3.netrun.io')
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise pytest.UsageError('--hosting-url must be an HTTPS origin without credentials or a path')
    return value.rstrip('/')


@pytest.fixture(scope='session')
def awake(site_url):
    # Netrun returns a temporary 503 HTML page while its container wakes up.
    return wait_until_ready(site_url)


@pytest.fixture
def site(site_url, awake):
    return Site(site_url)


@pytest.fixture(scope='session')
def public_pages(site_url, awake):
    client = Site(site_url)
    return {path: client.request(path) for path in PAGES}


@pytest.fixture
def account_factory(site_url, awake, pytestconfig, request):
    if not pytestconfig.getoption('--hosting-writes'):
        pytest.skip('Account creation requires --hosting-writes')
    accounts = []

    def create():
        account = new_account(site_url)
        record_account(account, request.node.nodeid)
        account.site.request('/tickets.html')
        response = account.site.request('/api/register', 'POST', registration(account), csrf=True)
        assert response.status == 201, f'Test account registration returned HTTP {response.status}'
        accounts.append(account)
        return account

    yield create
    for account in accounts:
        try:
            account.site.request('/api/logout', 'POST', {}, csrf=True)
        except AssertionError:
            pass  # A network failure must not mask the test result.


@pytest.fixture
def account(account_factory):
    return account_factory()


@pytest.fixture(scope='session')
def hosted_catalogue(site_url, awake):
    response = Site(site_url).request('/api/products')
    assert response.status == 200
    return response.json()['items']


@pytest.fixture
def hosted_ticket(hosted_catalogue):
    items = [item for item in hosted_catalogue if item['available']]
    if not items:
        pytest.skip('Requires an available ticket on the published website')
    return items[0]
