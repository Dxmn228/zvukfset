from decimal import Decimal
from uuid import uuid4

import pytest

from main.models import CartItem, Order, Product, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def buyer(client):
    user = User.objects.create_user(email='orders@example.com', name='Test', password='Test-password-123')
    client.force_login(user)
    return user


@pytest.fixture
def product():
    return Product.objects.create(name='Ticket', alias='order-ticket', short_description='Test', price=Decimal('67.05'), discount_percent=10)


def quote(client, product, quantity=2):
    response = client.put('/api/cart', {'items': [{'product_id': product.pk, 'quantity': quantity}]}, content_type='application/json')
    assert response.status_code == 200
    return response.json()


def place(client, cart, request_id=None):
    return client.post('/api/orders', {'quote': cart['quote'], 'request_id': str(request_id or uuid4())}, content_type='application/json')


def test_order_snapshot_discount_session_and_retry(client, buyer, product):
    cart = quote(client, product)
    assert cart['total'] == '120.70'  # 60.345 rounds to 60.35 per ticket
    assert cart['discount'] == '13.40'
    assert client.session['cart'] == [{'product_id': product.pk, 'quantity': 2}]
    request_id = uuid4()
    response = place(client, cart, request_id)
    assert response.status_code == 201
    assert place(client, cart, request_id).json()['order']['id'] == response.json()['order']['id']
    assert Order.objects.count() == 1
    assert not CartItem.objects.exists()
    assert client.session['cart'] == []
    assert buyer.actions.filter(action='place_order').count() == 1
    product.price = Decimal('1000.00')
    product.name = 'Changed'
    product.save()
    order = client.get('/api/orders').json()['items'][0]
    assert order['total'] == '120.70'
    assert order['items'][0]['name'] == 'Ticket'
    product.delete()
    assert Order.objects.get().items.get().product is None


@pytest.mark.parametrize('change', ['price', 'available', 'quantity'])
def test_changed_cart_rejected_without_side_effects(client, buyer, product, change):
    cart = quote(client, product)
    if change == 'quantity':
        CartItem.objects.filter(user=buyer).update(quantity=3)
    else:
        setattr(product, change, Decimal('100.00') if change == 'price' else False)
        product.save()
    assert place(client, cart).status_code == 409
    assert not Order.objects.exists()
    assert CartItem.objects.filter(user=buyer).exists()


def test_orders_and_cart_are_isolated(client, buyer, product):
    cart = quote(client, product)
    place(client, cart)
    other = User.objects.create_user(email='other@example.com', name='Other', password='Test-password-123')
    client.force_login(other)
    assert client.get('/api/orders').json()['items'] == []
    assert client.get('/api/cart').json()['items'] == []
    client.logout()
    assert client.get('/api/orders').status_code == 401
    assert place(client, cart).status_code == 401
    assert client.get('/account.html').status_code == 302


@pytest.mark.parametrize('quantity', [True, 1.5, '2', None])
def test_invalid_cart_preserves_previous_selection(client, buyer, product, quantity):
    quote(client, product)
    response = client.put('/api/cart', {'items': [{'product_id': product.pk, 'quantity': quantity}]}, content_type='application/json')
    assert response.status_code == 400
    assert CartItem.objects.get(user=buyer).quantity == 2


def test_empty_order_and_invalid_request_id(client, buyer):
    cart = client.get('/api/cart').json()
    assert place(client, cart).status_code == 400
    assert place(client, cart, 'invalid').status_code == 400
    assert not Order.objects.exists()


def test_product_history_feedback_and_policy(client, buyer, product):
    assert client.get(f'/api/products/{product.pk}').status_code == 200
    assert client.get('/api/actions').json()['last_viewed'][0]['id'] == product.pk
    response = client.post('/api/feedback', {'name': 'Test', 'email': buyer.email, 'subject': 'tickets', 'message': 'Test message long enough', 'rating': 5, 'privacy': True}, content_type='application/json')
    assert response.status_code == 201
    assert buyer.feedbacks.count() == 1
    response = client.get('/api/privacy/download')
    assert response.status_code == 200
    assert response['Content-Disposition'].startswith('attachment;')
    assert 'Ивкин Михаил Александрович' in response.content.decode()
    assert '<html' not in response.content.decode()
