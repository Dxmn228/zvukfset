import importlib.util
from pathlib import Path

import pytest
from django.test import Client, override_settings

DOMAIN = 'zvukfest.de3.netrun.io'


def load_site_settings():
    path = Path(__file__).resolve().parents[1] / 'zvukfest' / 'settings.py'
    spec = importlib.util.spec_from_file_location('zvukfest._domain_check', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def site_settings(monkeypatch):
    monkeypatch.delenv('DJANGO_ALLOWED_HOSTS', raising=False)
    monkeypatch.delenv('DJANGO_CSRF_TRUSTED_ORIGINS', raising=False)
    config = load_site_settings()
    with override_settings(ALLOWED_HOSTS=config.ALLOWED_HOSTS,
                           CSRF_TRUSTED_ORIGINS=config.CSRF_TRUSTED_ORIGINS,
                           DEBUG=False):
        yield config


def test_site_domain_allowed_but_other_hosts_rejected(client, site_settings):
    assert '*' not in site_settings.ALLOWED_HOSTS
    assert client.get('/', HTTP_HOST=DOMAIN).status_code == 200
    assert client.get('/css/style.css', HTTP_HOST=DOMAIN).status_code == 200
    assert client.get('/', HTTP_HOST='untrusted.example').status_code == 400
    assert client.get('/', HTTP_HOST=DOMAIN + '.untrusted.example').status_code == 400


@pytest.mark.parametrize('origin,secure', [('http://' + DOMAIN, False), ('https://' + DOMAIN, False), ('https://' + DOMAIN, True)])
def test_form_accepts_public_origin_including_tls_proxy(account_user, site_settings, origin, secure):
    client = Client(enforce_csrf_checks=True)
    client.force_login(account_user)
    client.get('/account.html', HTTP_HOST=DOMAIN, secure=secure)
    token = client.cookies['csrftoken'].value
    payload = dict(name='Domain checked', email=account_user.email)
    response = client.put('/api/profile', payload, content_type='application/json', HTTP_HOST=DOMAIN,
                          HTTP_ORIGIN=origin, HTTP_X_CSRFTOKEN=token, secure=secure)
    assert response.status_code == 200
    response = client.put('/api/profile', payload, content_type='application/json', HTTP_HOST=DOMAIN,
                          HTTP_ORIGIN='https://untrusted.example', HTTP_X_CSRFTOKEN=token, secure=secure)
    assert response.status_code == 403


def test_host_and_origin_can_be_overridden_without_code_changes(monkeypatch):
    monkeypatch.setenv('DJANGO_ALLOWED_HOSTS', ' example.com,localhost ')
    monkeypatch.setenv('DJANGO_CSRF_TRUSTED_ORIGINS', ' https://example.com ')
    config = load_site_settings()
    assert config.ALLOWED_HOSTS == ['example.com', 'localhost']
    assert config.CSRF_TRUSTED_ORIGINS == ['https://example.com']
