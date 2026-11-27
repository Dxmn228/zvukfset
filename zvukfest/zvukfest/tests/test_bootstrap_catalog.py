from datetime import date, time
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

from main.models import Category, Product


pytestmark = pytest.mark.django_db

EXPECTED = {
    'shaman-standard': ('Шаман', '2500.00', 'img/ticket-dance-floor.png'),
    'shaman-vip': ('Шаман', '4500.00', 'img/ticket-vip-zone.png'),
    'vanya-standard': ('Ваня Дмитриенко', '2200.00', 'img/ticket-dance-floor.png'),
    'vanya-vip': ('Ваня Дмитриенко', '3900.00', 'img/ticket-vip-zone.png'),
    'stas-standard': ('Стас Михайлов', '3500.00', 'img/ticket-dance-floor.png'),
    'stas-vip': ('Стас Михайлов', '6500.00', 'img/ticket-vip-zone.png'),
    'anna-standard': ('Анна Асти', '3000.00', 'img/ticket-dance-floor.png'),
    'anna-vip': ('Анна Асти', '5500.00', 'img/ticket-vip-zone.png'),
}

SCHEDULE = {
    'Шаман': time(18, 0),
    'Ваня Дмитриенко': time(19, 30),
    'Стас Михайлов': time(21, 0),
    'Анна Асти': time(22, 30),
}


def bootstrap_catalog():
    output = StringIO()
    call_command('bootstrap_catalog', stdout=output)
    return output.getvalue()


def test_bootstrap_creates_every_permanent_ticket_with_schedule_and_image():
    assert '8 tickets created' in bootstrap_catalog()
    products = Product.objects.filter(alias__in=EXPECTED).prefetch_related('categories')
    assert products.count() == len(EXPECTED)
    assert Category.objects.filter(name__in=SCHEDULE).count() == len(SCHEDULE)

    for product in products:
        artist, price, image = EXPECTED[product.alias]
        assert product.price == Decimal(price)
        assert product.image == image
        assert product.available
        assert list(product.categories.values_list('name', flat=True)) == [artist]
        assert (Path(settings.BASE_DIR) / 'frontend' / image).is_file()

        category = product.categories.get()
        assert category.performance_date == date(2027, 7, 16)
        assert category.performance_time == SCHEDULE[artist]


def test_bootstrap_is_idempotent_and_preserves_admin_changes():
    bootstrap_catalog()
    product = Product.objects.get(alias='shaman-standard')
    category = product.categories.get()
    product.name = 'Изменённый администратором билет'
    product.price = Decimal('7777.00')
    product.save()
    category.performance_time = time(17, 45)
    category.save()

    assert '0 tickets created' in bootstrap_catalog()
    product.refresh_from_db()
    category.refresh_from_db()
    assert Product.objects.filter(alias__in=EXPECTED).count() == 8
    assert Category.objects.filter(name__in=SCHEDULE).count() == 4
    assert product.name == 'Изменённый администратором билет'
    assert product.price == Decimal('7777.00')
    assert category.performance_time == time(17, 45)


def test_all_permanent_tickets_are_returned_by_api_and_can_be_added_to_cart(client, account_user):
    bootstrap_catalog()
    response = client.get('/api/products', {'sort': 'price'})
    assert response.status_code == 200
    items = {item['alias']: item for item in response.json()['items'] if item['alias'] in EXPECTED}
    assert set(items) == set(EXPECTED)

    for alias, item in items.items():
        artist, price, image = EXPECTED[alias]
        assert Decimal(item['unit_price']) == Decimal(price)
        assert item['image'] == image
        assert len(item['categories']) == 1
        category = item['categories'][0]
        assert category['name'] == artist
        assert category['performance_date'] == '2027-07-16'
        assert category['performance_time'] == SCHEDULE[artist].strftime('%H:%M')
        assert 'performance_price' not in category

    client.force_login(account_user)
    selection = [{'product_id': item['id'], 'quantity': 1} for item in items.values()]
    cart = client.put('/api/cart', {'items': selection}, content_type='application/json')
    assert cart.status_code == 200
    cart_items = {item['product_id']: item for item in cart.json()['items']}
    assert len(cart_items) == 8
    for item in items.values():
        assert cart_items[item['id']]['image'] == item['image']


def test_new_and_blank_tickets_receive_fallback_image():
    default_ticket = Product.objects.create(
        name='Новый билет', alias='new-default-image', short_description='Описание', price=100)
    blank_ticket = Product.objects.create(
        name='Билет без картинки', alias='new-blank-image', short_description='Описание', price=100,
        image='')
    assert default_ticket.image == 'img/ticket.svg'
    assert blank_ticket.image == 'img/ticket.svg'
    assert (Path(settings.BASE_DIR) / 'frontend/img/ticket.svg').is_file()
