"""Run through scripts/run_postgres_tests.py; skipped by the SQLite suite."""
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from django.db import IntegrityError, connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client

from main.models import CartItem, Order, Product, User

pytestmark = [pytest.mark.django_db(transaction=True),
              pytest.mark.skipif(connection.vendor != 'postgresql', reason='Requires isolated PostgreSQL runner')]


def test_migration_preserves_existing_users_products_and_cart():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes('main')
    previous = [('main', '0001_initial')]
    try:
        executor.migrate(previous)
        apps = executor.loader.project_state(previous).apps
        user = apps.get_model('main', 'User').objects.create(name='Migration user', email='migration@example.com', password='unusable-test-hash')
        product = apps.get_model('main', 'Product').objects.create(name='Old ticket', alias='old-ticket', price='100.00', short_description='Before migration')
        apps.get_model('main', 'CartItem').objects.create(user_id=user.pk, product_id=product.pk, quantity=2)
        MigrationExecutor(connection).migrate(latest)
        assert User.objects.get(pk=user.pk).email == 'migration@example.com'
        assert Product.objects.get(pk=product.pk).discount_percent == 0
        assert CartItem.objects.get(user_id=user.pk).quantity == 2
        assert Order.objects.count() == 0
        assert MigrationExecutor(connection).migration_plan(latest) == []
    finally:
        MigrationExecutor(connection).migrate(latest)


def test_foreign_key_rejects_nonexistent_product(account_user):
    with pytest.raises(IntegrityError), transaction.atomic():
        CartItem.objects.create(user=account_user, product_id=999999999, quantity=1)
        # PostgreSQL checks deferred foreign keys at commit; force them here too.
        connection.check_constraints()
    assert not CartItem.objects.exists()


@pytest.mark.parametrize('same_request', [True, False])
def test_simultaneous_checkout_cannot_create_duplicate_orders(account_user, ticket_product, same_request):
    CartItem.objects.create(user=account_user, product=ticket_product, quantity=2)
    clients = [Client(), Client()]
    for client in clients:
        client.force_login(account_user)
    quote = clients[0].get('/api/cart').json()['quote']
    request_ids = [str(uuid4()), str(uuid4())]
    if same_request:
        request_ids[1] = request_ids[0]
    ready = Barrier(2)

    def checkout(index):
        connections.close_all()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET lock_timeout TO '5s'")
            ready.wait(timeout=10)
            result = clients[index].post('/api/orders', {'quote': quote, 'request_id': request_ids[index]}, content_type='application/json')
            return result.status_code, result.json()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(checkout, [0, 1]))
    assert sorted(status for status, _ in results) == ([200, 201] if same_request else [201, 400])
    assert Order.objects.count() == 1
    assert Order.objects.get().total == 200
    assert not CartItem.objects.exists()
    assert account_user.actions.filter(action='place_order').count() == 1
    if same_request:
        assert results[0][1]['order']['id'] == results[1][1]['order']['id']


def test_data_and_login_survive_isolated_database_restart(client, account_user, ticket_product):
    project = os.environ.get('TEST_POSTGRES_PROJECT', '')
    container = os.environ.get('TEST_POSTGRES_CONTAINER', '')
    if not project or not container:
        pytest.skip('Restart is allowed only by the isolated runner')
    assert re.fullmatch(r'zvukfest-test-[a-f0-9]{32}', project)
    inspected = json.loads(subprocess.check_output(['docker', 'inspect', container], text=True, encoding='utf-8'))[0]
    labels = inspected['Config']['Labels']
    assert labels['com.docker.compose.project'] == project
    assert labels['com.docker.compose.service'] == 'db'
    assert connection.settings_dict['NAME'] == 'test_zvukfest_tests'
    client.force_login(account_user)
    CartItem.objects.create(user=account_user, product=ticket_product, quantity=2)
    quote = client.get('/api/cart').json()['quote']
    response = client.post('/api/orders', {'quote': quote, 'request_id': str(uuid4())}, content_type='application/json')
    assert response.status_code == 201
    order_id = response.json()['order']['id']
    CartItem.objects.create(user=account_user, product=ticket_product, quantity=3)
    connections.close_all()
    subprocess.run(['docker', 'restart', container], check=True, capture_output=True, timeout=45)
    deadline = time.monotonic() + 30
    while True:
        try:
            connection.ensure_connection()
            break
        except Exception:
            connection.close()
            if time.monotonic() >= deadline:
                raise
            time.sleep(.25)
    assert User.objects.get(pk=account_user.pk).check_password('Local-test-password-123')
    assert client.get('/api/profile').status_code == 200
    assert client.get('/api/cart').json()['items'][0]['quantity'] == 3
    assert client.get('/api/orders').json()['items'][0]['id'] == order_id
    assert Order.objects.get(pk=order_id).items.get().quantity == 2
