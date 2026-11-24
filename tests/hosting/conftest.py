import os
from urllib.parse import urlsplit

import pytest

from hosting_support import PAGES, Site


def pytest_addoption(parser):
    group = parser.getgroup('hosting')
    group.addoption('--hosting-url', default=os.environ.get('HOSTING_BASE_URL'))
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
    # Allow a sleeping free instance to start once; normal requests use 20 s.
    result = Site(site_url, timeout=60).request('/')
    assert result.status == 200, f'Homepage warm-up returned HTTP {result.status}'


@pytest.fixture
def site(site_url, awake):
    return Site(site_url)


@pytest.fixture(scope='session')
def public_pages(site_url, awake):
    client = Site(site_url)
    return {path: client.request(path) for path in PAGES}
