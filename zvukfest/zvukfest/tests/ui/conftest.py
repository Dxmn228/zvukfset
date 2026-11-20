from decimal import Decimal
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect

from main.models import Product, User


TEST_PASSWORD = 'Browser-test-password-123'


@pytest.fixture(scope='session')
def browser_context_args(browser_context_args):
    return {**browser_context_args, 'viewport': {'width': 1440, 'height': 1000}, 'locale': 'ru-RU'}


@pytest.fixture
def ui_page(page, live_server):
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def check_resource(response):
        path = urlparse(response.url).path
        if response.url.startswith(live_server.url) and path.startswith(('/css/', '/js/', '/img/')):
            if response.status >= 400:
                errors.append(f'{response.status}: {path}')

    page.on('response', check_resource)

    def local_resources_only(route):
        if route.request.url.startswith(live_server.url + '/'):
            route.continue_()
        else:
            # Third-party maps are outside this suite; no external network needed.
            route.fulfill(status=200, content_type='text/html', body='')

    page.context.route('**/*', local_resources_only)
    yield page
    assert not errors, '\n'.join(errors)


@pytest.fixture
def catalogue(transactional_db):
    return [
        Product.objects.create(name='Обычный билет', alias='ui-standard', short_description='Один день фестиваля', price=Decimal('67.00')),
        Product.objects.create(name='VIP-билет', alias='ui-vip', short_description='Все дни фестиваля', price=Decimal('1500.00')),
        Product.objects.create(name='Распроданный билет', alias='ui-sold-out', short_description='Недоступен', price=Decimal('500.00'), available=False),
    ]


@pytest.fixture
def registered_user(transactional_db):
    return User.objects.create_user(email='browser@example.com', name='Тестовый зритель', password=TEST_PASSWORD)


@pytest.fixture
def sign_in(ui_page, live_server, registered_user):
    def login():
        ui_page.goto(live_server.url + '/tickets.html')
        ui_page.locator('#login-email').fill(registered_user.email)
        ui_page.locator('#login-password').fill(TEST_PASSWORD)
        ui_page.locator('#login button[type="submit"]').click()
        expect(ui_page).to_have_url(live_server.url + '/account.html')
        expect(ui_page.locator('#acc-email')).to_have_value(registered_user.email)
        expect(ui_page.locator('#search-list li').first).to_be_visible()
        return ui_page
    return login


@pytest.fixture
def signed_in_page(sign_in):
    return sign_in()
