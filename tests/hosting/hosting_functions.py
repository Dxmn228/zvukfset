"""Functional assertions against the deployed API; no Django test client or ORM."""
from decimal import Decimal, ROUND_HALF_UP
import secrets
from urllib.parse import urlencode
from uuid import uuid4

import pytest

from hosting_accounts import new_account, registration
from hosting_support import Site

pytestmark = [pytest.mark.functional, pytest.mark.writes]


def write(account, path, data, method='POST'):
    return account.site.request(path, method, data, csrf=True)


def selection(ticket, quantity=1):
    return {'items': [{'product_id': ticket['id'], 'quantity': quantity}]}


def test_registration_validation_on_server(site, site_url):
    data = registration(new_account(site_url))
    site.request('/tickets.html')
    cases = [({'email': 'bad-email'}, 'email'), ({'username': 'x'}, 'username'),
             ({'password': 'short', 'password_confirm': 'short'}, 'password'),
             ({'password_confirm': 'different'}, 'password_confirm'),
             ({'terms': False}, 'terms'), ({'privacy': False}, 'privacy'), ({'phone': 'abc'}, 'phone')]
    for change, field in cases:
        response = site.request('/api/register', 'POST', {**data, **change}, csrf=True)
        assert response.status == 400, f'Registration accepted invalid {field}'
        assert field in response.json()['errors']
        assert site.request('/api/profile').status == 401


def test_duplicate_email_and_repeated_login(account):
    response = write(account, '/api/register', {**registration(account), 'email': account.email.upper()})
    assert response.status == 400 and 'email' in response.json()['errors']
    for remember in (False, True):
        assert account.login(remember=remember).status == 200
        cookie = account.site.cookie('sessionid')
        assert cookie is not None
        assert (cookie.expires is not None) is remember
        assert account.site.request('/api/profile').json()['email'] == account.email


def test_account_switch_and_wrong_password(account_factory):
    first, second = account_factory(), account_factory()
    old = first.site.cookie('sessionid').value
    assert second.login(site=first.site).status == 200
    rotated = first.site.cookie('sessionid').value != old
    assert rotated, 'Switching accounts must rotate the session identifier'
    assert first.site.request('/api/profile').json()['email'] == second.email
    assert write(first, '/api/logout', {}).status == 200
    response = write(first, '/api/login', {'email': second.email, 'password': 'Deliberately-wrong-password'})
    assert response.status == 401
    assert first.site.request('/api/profile').status == 401


def test_profile_validation_role_and_isolation(account_factory):
    first, second = account_factory(), account_factory()
    other_profile = second.site.request('/api/profile').json()
    response = write(first, '/api/profile', {'name': 'Changed', 'email': second.email.upper()}, 'PUT')
    assert response.status == 400
    assert first.site.request('/api/profile').json()['name'] == first.name
    for change, field in [({'name': 'x'}, 'name'), ({'email': 'invalid'}, 'email'), ({'phone': 'abc'}, 'phone')]:
        response = write(first, '/api/profile', {'name': first.name, 'email': first.email, **change}, 'PUT')
        assert response.status == 400 and field in response.json()['errors']
    other_id = second.site.request('/api/cart').json()['user_id']
    response = write(first, '/api/profile', dict(name='Hosting changed', email=first.email,
                     phone='+79990000000', role='admin', user_id=other_id), 'PUT')
    assert response.status == 200
    current = first.site.request(f'/api/profile?user_id={other_id}').json()
    assert current['email'] == first.email and current['role'] == 'user'
    assert current['name'] == 'Hosting changed'
    assert second.site.request('/api/profile').json() == other_profile
    assert first.site.request('/admin/', follow=False).status == 302


def test_password_change_preserves_current_session_revokes_other(account, site_url):
    other = Site(site_url)
    assert account.login(other).status == 200
    new_password = secrets.token_urlsafe(24)
    valid = dict(old_password=account.password, new_password=new_password, confirm_password=new_password)
    for change, field in [({'old_password': 'wrong'}, 'old_password'),
                          ({'confirm_password': 'different'}, 'confirm_password'),
                          ({'new_password': 'short', 'confirm_password': 'short'}, 'new_password')]:
        response = write(account, '/api/password', {**valid, **change})
        assert response.status == 400 and field in response.json()['errors']
    assert write(account, '/api/password', valid).status == 200
    assert account.site.request('/api/profile').status == 200
    assert other.request('/api/profile').status == 401
    assert write(account, '/api/logout', {}).status == 200
    assert account.login().status == 401
    account.password = new_password
    assert account.login().status == 200


def test_feedback_validation_history_and_isolation(account_factory):
    first, second = account_factory(), account_factory()
    data = dict(name=first.name, email=first.email, subject='tickets',
                message='Hosting functional test ' + uuid4().hex, rating=5, privacy=True)
    for change, field in [({'subject': 'invalid'}, 'subject'), ({'message': 'short'}, 'message'),
                          ({'message': 'x' * 2001}, 'message'), ({'rating': 0}, 'rating'),
                          ({'rating': 6}, 'rating'), ({'rating': 1.5}, 'rating'),
                          ({'email': 'invalid'}, 'email'), ({'privacy': False}, 'privacy')]:
        response = write(first, '/api/feedback', {**data, **change})
        assert response.status == 400 and field in response.json()['errors']
    assert first.site.request('/api/feedback').json()['items'] == []
    assert write(first, '/api/feedback', data).status == 201
    assert first.site.request('/api/feedback').json()['items'][0]['message'] == data['message']
    first_id = first.site.request('/api/cart').json()['user_id']
    assert second.site.request(f'/api/feedback?user_id={first_id}').json()['items'] == []
    actions = second.site.request(f'/api/actions?user_id={first_id}').json()['items']
    assert not any(item['action'] == 'send_feedback' for item in actions)


def test_search_history_bounds_and_validation(account, hosted_catalogue):
    queries = ['hosting-' + uuid4().hex[:12] for _ in range(7)]
    for query in queries + [queries[4]]:
        response = account.site.request('/api/search?' + urlencode({'q': query}))
        assert response.status == 200
    before = account.site.request('/api/actions').json()['search_history']
    assert before == [queries[i] for i in (4, 6, 5, 3, 2)]
    for query in ('', 'x', 'x' * 101):
        assert account.site.request('/api/search?' + urlencode({'q': query})).status == 400
    assert account.site.request('/api/actions').json()['search_history'] == before
    assert account.site.request('/api/search?' + urlencode({'q': "' OR 1=1 --"})).status == 200
    # Work with the published catalogue; never create or alter public tickets.
    ids = [item['id'] for item in hosted_catalogue[:7]]
    if ids:
        for product_id in ids + [ids[0]]:
            assert account.site.request(f'/api/products/{product_id}').status == 200
        expected = [ids[0]] + list(reversed(ids[1:]))[:4]
        assert [p['id'] for p in account.site.request('/api/actions').json()['last_viewed']] == expected


def test_cart_validation_totals_and_isolation(account_factory, hosted_ticket):
    first, second = account_factory(), account_factory()
    response = write(first, '/api/cart', selection(hosted_ticket, 2), 'PUT')
    assert response.status == 200
    cart = response.json()
    item = cart['items'][0]
    unit = (Decimal(item['price']) * (100 - item['discount_percent']) / 100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    assert Decimal(cart['total']) == unit * 2
    assert Decimal(cart['subtotal']) - Decimal(cart['discount']) == Decimal(cart['total'])
    for quantity in (0, 21, -1, True, 1.5, '2', None):
        assert write(first, '/api/cart', selection(hosted_ticket, quantity), 'PUT').status == 400
        assert first.site.request('/api/cart').json()['items'] == cart['items']
    for data in ({'items': None}, {'items': [{}]}, {'items': selection(hosted_ticket)['items'] * 2}):
        assert write(first, '/api/cart', data, 'PUT').status == 400
    assert write(first, '/api/cart', {'items': [{'product_id': -1, 'quantity': 1}]}, 'PUT').status == 409
    other = second.site.request(f'/api/cart?user_id={cart["user_id"]}').json()
    assert other['items'] == []
    assert write(first, '/api/cart', {'items': []}, 'PUT').json()['items'] == []


def test_order_invalid_empty_stale_and_retry(account_factory, hosted_ticket):
    first, second = account_factory(), account_factory()
    assert write(first, '/api/orders', {'request_id': 'invalid'}).status == 400
    assert write(first, '/api/orders', {'request_id': str(uuid4()), 'quote': ''}).status == 400
    quote = write(first, '/api/cart', selection(hosted_ticket), 'PUT').json()['quote']
    assert write(first, '/api/cart', selection(hosted_ticket, 2), 'PUT').status == 200
    assert write(first, '/api/orders', {'request_id': str(uuid4()), 'quote': quote}).status == 409
    assert first.site.request('/api/orders').json()['items'] == []
    cart = first.site.request('/api/cart').json()
    data = {'request_id': str(uuid4()), 'quote': cart['quote']}
    order = write(first, '/api/orders', data)
    assert order.status == 201
    snapshot = order.json()['order']
    assert snapshot['total'] == cart['total'] and snapshot['items'][0]['quantity'] == 2
    assert write(first, '/api/orders', data).json()['order']['id'] == snapshot['id']
    assert first.site.request('/api/orders').json()['items'] == [snapshot]
    assert first.site.request('/api/cart').json()['items'] == []
    assert second.site.request(f'/api/orders?user_id={cart["user_id"]}').json()['items'] == []


def test_authenticated_writes_require_csrf(account):
    for path, method in [('/api/profile', 'PUT'), ('/api/cart', 'PUT'), ('/api/password', 'POST'),
                          ('/api/orders', 'POST'), ('/api/logout', 'POST')]:
        response = account.site.request(path, method, {})
        assert response.status == 403
        foreign = account.site.request(path, method, {}, csrf=True, headers={'Origin': 'https://untrusted.example'})
        assert foreign.status == 403
    assert account.site.request('/api/profile').status == 200
