from io import StringIO

import pytest
from django.core.management import call_command

from main.models import User


pytestmark = pytest.mark.django_db
PASSWORD = 'Bootstrap-test-only-82!'


@pytest.fixture(autouse=True)
def bootstrap_secrets(monkeypatch):
    monkeypatch.setenv('DJANGO_SUPERUSER_EMAIL', 'Hosting.Admin@example.com')
    monkeypatch.setenv('DJANGO_SUPERUSER_NAME', 'Hosting owner')
    monkeypatch.setenv('DJANGO_SUPERUSER_PASSWORD', PASSWORD)


def run_bootstrap():
    output = StringIO()
    call_command('bootstrap_admin', stdout=output, stderr=output)
    text = output.getvalue()
    assert PASSWORD not in text
    assert 'Hosting.Admin@example.com' not in text
    return text


def test_bootstrap_admin_can_log_in_and_open_product_form(client):
    assert 'Admin created' in run_bootstrap()
    user = User.objects.get(email='hosting.admin@example.com')
    assert user.is_staff and user.check_password(PASSWORD)
    assert user.password != PASSWORD
    response = client.post('/admin/login/', {
        'username': user.email, 'password': PASSWORD, 'next': '/admin/',
    })
    assert response.status_code == 302
    assert client.get('/admin/main/product/add/').status_code == 200


def test_repeated_start_preserves_admin_password_and_name(monkeypatch):
    run_bootstrap()
    original = User.objects.get()
    monkeypatch.setenv('DJANGO_SUPERUSER_PASSWORD', 'Different-test-password-55!')
    monkeypatch.setenv('DJANGO_SUPERUSER_NAME', 'Changed')
    assert 'unchanged' in run_bootstrap()
    original.refresh_from_db()
    assert original.check_password(PASSWORD)
    assert original.name == 'Hosting owner'
    assert User.objects.count() == 1


def test_existing_regular_user_is_never_promoted():
    original = User.objects.create_user('hosting.admin@example.com', 'Customer', PASSWORD)
    # Also cover older records with non-normalized email casing.
    User.objects.filter(pk=original.pk).update(email='Hosting.Admin@example.com')
    assert 'regular user' in run_bootstrap()
    original.refresh_from_db()
    assert original.role == 'user' and original.name == 'Customer'
    assert original.check_password(PASSWORD)
    assert User.objects.count() == 1


def test_missing_secrets_do_nothing(monkeypatch):
    for field in ('EMAIL', 'NAME', 'PASSWORD'):
        monkeypatch.delenv('DJANGO_SUPERUSER_' + field)
    assert run_bootstrap() == ''
    assert not User.objects.exists()


@pytest.mark.parametrize(('field', 'value'), [
    ('EMAIL', ''), ('NAME', ''), ('PASSWORD', ''),
    ('EMAIL', 'invalid-email'), ('NAME', 'x' * 101),
    ('PASSWORD', 'short'), ('PASSWORD', '1234567890123456'),
    ('PASSWORD', 'hosting.admin@example.com'),
])
def test_invalid_secrets_skip_creation_without_breaking_startup(monkeypatch, field, value):
    monkeypatch.setenv('DJANGO_SUPERUSER_' + field, value)
    assert 'skipped' in run_bootstrap()
    assert not User.objects.exists()


def test_removing_secrets_preserves_created_admin(monkeypatch):
    run_bootstrap()
    for field in ('EMAIL', 'NAME', 'PASSWORD'):
        monkeypatch.delenv('DJANGO_SUPERUSER_' + field)
    run_bootstrap()
    assert User.objects.get().check_password(PASSWORD)
