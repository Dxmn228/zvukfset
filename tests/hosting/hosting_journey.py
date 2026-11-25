import copy
import secrets
from uuid import uuid4

import pytest

from hosting_support import Site

pytestmark = [pytest.mark.writes, pytest.mark.functional]


def test_registration_session_cart_order_and_relogin(site, site_url, record_property):
    catalogue = site.request('/api/products').json()['items']
    available = [item for item in catalogue if item['available']]
    if not available:
        pytest.skip('Add an available ticket before running the complete demo purchase')
    run_id = uuid4().hex
    email = f'hosting-test-{run_id}@example.invalid'
    password = secrets.token_urlsafe(24)
    record_property('test_account_email', email)  # Identification for manual cleanup, no password recorded.
    site.request('/tickets.html')
    registration = dict(username='Hosting test ' + run_id[:8], email=email, password=password,
                        password_confirm=password, terms=True, privacy=True)
    response = site.request('/api/register', 'POST', registration, csrf=True)
    assert response.status == 201, f'Registration returned HTTP {response.status}'
    cookie = site.cookie('sessionid')
    cookie_flags = {
        'Secure': cookie is not None and cookie.secure,
        'HttpOnly': cookie is not None and cookie.has_nonstandard_attr('HttpOnly'),
        'SameSite': cookie is not None and cookie.get_nonstandard_attr('SameSite', '').lower() in ('lax', 'strict'),
    }
    assert site.request('/api/profile').json()['email'] == email
    profile = site.request('/api/profile', 'PUT', {'name': 'Hosting test updated', 'email': email}, csrf=True)
    assert profile.status == 200
    assert site.request('/api/profile').json()['name'] == 'Hosting test updated'
    feedback = site.request('/api/feedback', 'POST', {
        'name': 'Hosting test', 'email': email, 'subject': 'tickets',
        'message': 'Automated hosting demonstration check ' + run_id, 'privacy': True,
    }, csrf=True)
    assert feedback.status == 201
    assert len(site.request('/api/feedback').json()['items']) == 1
    selection = {'items': [{'product_id': available[0]['id'], 'quantity': 1}]}
    assert site.request('/api/cart', 'PUT', selection, csrf=True).status == 200

    # A separate HTTP client shares only the browser cookie, not an in-memory cart.
    resumed = Site(site_url)
    for cookie in site.cookies:
        resumed.cookies.set_cookie(copy.copy(cookie))
    cart = resumed.request('/api/cart').json()
    assert len(cart['items']) == 1 and cart['items'][0]['quantity'] == 1
    assert resumed.request('/api/cart', 'PUT', {'items': []}, csrf=True).json()['items'] == []
    cart_response = resumed.request('/api/cart', 'PUT', selection, csrf=True)
    assert cart_response.status == 200
    payload = {'request_id': str(uuid4()), 'quote': cart_response.json()['quote']}
    order = resumed.request('/api/orders', 'POST', payload, csrf=True)
    assert order.status == 201
    order_id = order.json()['order']['id']
    record_property('demo_order_id', order_id)
    again = resumed.request('/api/orders', 'POST', payload, csrf=True)
    assert again.status == 200 and again.json()['order']['id'] == order_id
    assert resumed.request('/api/cart').json()['items'] == []
    assert resumed.request('/api/logout', 'POST', {}, csrf=True).status == 200
    assert site.request('/api/profile').status == 401  # The copied old cookie is also invalidated.
    resumed.request('/tickets.html')
    login = resumed.request('/api/login', 'POST', {'email': email, 'password': password, 'remember': True}, csrf=True)
    assert login.status == 200
    history = resumed.request('/api/orders').json()['items']
    assert [item['id'] for item in history] == [order_id]
    assert resumed.request('/api/logout', 'POST', {}, csrf=True).status == 200
    # Check security after the journey and logout; never include cookie values in reports.
    for flag, enabled in cookie_flags.items():
        assert enabled, f'Session cookie must set {flag}'
