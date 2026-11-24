from decimal import Decimal

import pytest

from main.models import Product, User

TEST_PASSWORD = 'Local-test-password-123'


@pytest.fixture
def account_user(db):
    return User.objects.create_user(email='account@example.com', name='Test user', password=TEST_PASSWORD)


@pytest.fixture
def ticket_product(db):
    return Product.objects.create(name='Test ticket', alias='test-ticket', short_description='Festival admission', price=Decimal('100.00'))


@pytest.fixture
def registration_data():
    return dict(username='New user', email='new@example.com', password=TEST_PASSWORD,
                password_confirm=TEST_PASSWORD, terms=True, privacy=True)
