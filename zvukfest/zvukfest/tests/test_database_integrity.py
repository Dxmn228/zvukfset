from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction

from main.models import CartItem, Feedback, Order, OrderItem, Product, User

pytestmark = pytest.mark.django_db


def test_unique_email_and_cart_pair_enforced_in_database(account_user, ticket_product):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(email=account_user.email, name='Duplicate')
    CartItem.objects.create(user=account_user, product=ticket_product)
    with pytest.raises(IntegrityError), transaction.atomic():
        CartItem.objects.create(user=account_user, product=ticket_product)
    assert User.objects.count() == 1
    assert CartItem.objects.count() == 1


def test_rating_discount_and_not_null_constraints(account_user, ticket_product):
    with pytest.raises(IntegrityError), transaction.atomic():
        Feedback.objects.create(user=account_user, name='Test', email=account_user.email,
                                subject='tickets', message='Invalid rating', rating=6)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=ticket_product.pk).update(discount_percent=101)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=ticket_product.pk).update(name=None)
    ticket_product.refresh_from_db()
    assert ticket_product.discount_percent == 0
    assert not Feedback.objects.exists()


def test_order_write_failure_rolls_back_order_cart_and_journal(client, account_user, ticket_product):
    client.force_login(account_user)
    CartItem.objects.create(user=account_user, product=ticket_product, quantity=2)
    cart = client.get('/api/cart').json()
    with patch.object(OrderItem.objects, 'bulk_create', side_effect=IntegrityError('Injected database failure')):
        with pytest.raises(IntegrityError, match='Injected database failure'):
            client.post('/api/orders', {'quote': cart['quote'], 'request_id': str(uuid4())}, content_type='application/json')
    assert not Order.objects.exists()
    assert not OrderItem.objects.exists()
    assert CartItem.objects.get(user=account_user).quantity == 2
    assert not account_user.actions.filter(action='place_order').exists()
    assert client.session['cart'] == [{'product_id': ticket_product.pk, 'quantity': 2}]
