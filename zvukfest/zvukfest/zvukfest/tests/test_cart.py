from decimal import Decimal

import pytest

from main.models import CartItem, Product, User


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        email="buyer@example.com",
        name="Покупатель",
        password="Test-password-123",
    )


@pytest.fixture
def ticket():
    return Product.objects.create(
        name="Билет на один день",
        alias="one-day",
        short_description="Доступ ко всем сценам",
        price=Decimal("2500.00"),
        available=True,
    )


def test_guest_cannot_open_cart(client):
    response = client.get("/api/cart")

    assert response.status_code == 401


def test_user_can_add_ticket(client, user, ticket):
    client.force_login(user)

    response = client.put(
        "/api/cart",
        data={
            "items": [
                {"product_id": ticket.id, "quantity": 2},
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 200

    item = CartItem.objects.get(user=user, product=ticket)
    assert item.quantity == 2


def test_user_can_clear_cart(client, user, ticket):
    CartItem.objects.create(
        user=user,
        product=ticket,
        quantity=2,
    )
    client.force_login(user)

    response = client.put(
        "/api/cart",
        data={"items": []},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert not CartItem.objects.filter(user=user).exists()


@pytest.mark.parametrize("quantity", [0, -1, 21])
def test_invalid_quantity_does_not_change_cart(
    client, user, ticket, quantity
):
    item = CartItem.objects.create(
        user=user,
        product=ticket,
        quantity=2,
    )
    client.force_login(user)

    response = client.put(
        "/api/cart",
        data={
            "items": [
                {"product_id": ticket.id, "quantity": quantity},
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 400

    item.refresh_from_db()
    assert item.quantity == 2