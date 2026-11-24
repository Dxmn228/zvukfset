from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

from main.models import Feedback, User, UserAction
from .conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db
NEW_PASSWORD = 'Changed-test-password-456'


@pytest.mark.parametrize('change,field', [
    ({'email': 'bad-email'}, 'email'),
    ({'password': 'short', 'password_confirm': 'short'}, 'password'),
    ({'password_confirm': 'different-password'}, 'password_confirm'),
    ({'terms': False}, 'terms'), ({'privacy': False}, 'privacy'),
    ({'username': 'x'}, 'username'), ({'phone': 'abc'}, 'phone'),
])
def test_invalid_registration_cannot_bypass_browser(client, registration_data, change, field):
    response = client.post('/api/register', {**registration_data, **change}, content_type='application/json')
    assert response.status_code == 400
    assert field in response.json()['errors']
    assert not User.objects.exists()
    assert not UserAction.objects.exists()
    assert '_auth_user_id' not in client.session


def test_duplicate_email_is_case_insensitive(client, account_user, registration_data):
    response = client.post('/api/register', {**registration_data, 'email': account_user.email.upper()}, content_type='application/json')
    assert response.status_code == 400
    assert 'email' in response.json()['errors']
    assert User.objects.count() == 1
    assert account_user.check_password(TEST_PASSWORD)


@pytest.mark.parametrize('change,field', [
    ({'old_password': 'wrong'}, 'old_password'),
    ({'confirm_password': 'different'}, 'confirm_password'),
    ({'new_password': 'short', 'confirm_password': 'short'}, 'new_password'),
])
def test_password_validation_preserves_old_password(client, account_user, change, field):
    client.force_login(account_user)
    data = dict(old_password=TEST_PASSWORD, new_password=NEW_PASSWORD, confirm_password=NEW_PASSWORD)
    response = client.post('/api/password', {**data, **change}, content_type='application/json')
    assert response.status_code == 400
    assert field in response.json()['errors']
    account_user.refresh_from_db()
    assert account_user.check_password(TEST_PASSWORD)
    assert not account_user.actions.filter(action='change_password').exists()


def test_password_change_preserves_current_session_and_revokes_others(client, account_user):
    client.force_login(account_user)
    other = Client()
    other.force_login(account_user)
    response = client.post('/api/password', dict(old_password=TEST_PASSWORD, new_password=NEW_PASSWORD,
                                               confirm_password=NEW_PASSWORD), content_type='application/json')
    assert response.status_code == 200
    account_user.refresh_from_db()
    assert account_user.password != NEW_PASSWORD
    assert account_user.check_password(NEW_PASSWORD)
    assert not account_user.check_password(TEST_PASSWORD)
    assert client.get('/api/profile').status_code == 200
    assert other.get('/api/profile').status_code == 401
    assert account_user.actions.filter(action='change_password').count() == 1
    client.post('/api/logout')
    assert client.post('/api/login', dict(email=account_user.email, password=TEST_PASSWORD), content_type='application/json').status_code == 401
    assert client.post('/api/login', dict(email=account_user.email, password=NEW_PASSWORD), content_type='application/json').status_code == 200


def test_profile_duplicate_email_rejects_entire_update(client, account_user):
    User.objects.create_user(email='taken@example.com', name='Other', password=TEST_PASSWORD)
    client.force_login(account_user)
    response = client.put('/api/profile', dict(name='Changed', email='TAKEN@example.com'), content_type='application/json')
    assert response.status_code == 400
    account_user.refresh_from_db()
    assert account_user.name == 'Test user'
    assert account_user.email == 'account@example.com'


@pytest.mark.parametrize('path,method', [('/api/profile', 'get'), ('/api/profile', 'put'),
    ('/api/password', 'post'), ('/api/actions', 'get'), ('/api/feedback', 'get'),
    ('/api/cart', 'get'), ('/api/cart', 'put'), ('/api/orders', 'get'), ('/api/orders', 'post')])
def test_guest_private_api_is_denied(client, path, method):
    assert getattr(client, method)(path, {}, content_type='application/json').status_code == 401


def test_other_users_profile_feedback_and_actions_cannot_be_read_or_modified(client, account_user):
    other = User.objects.create_user(email='private@example.com', name='Private', password=TEST_PASSWORD)
    Feedback.objects.create(user=other, name=other.name, email=other.email, subject='tickets', message='Private message')
    UserAction.objects.create(user=other, action='private-action')
    client.force_login(account_user)
    assert client.get(f'/api/feedback?user_id={other.pk}').json()['items'] == []
    assert client.get(f'/api/actions?user_id={other.pk}').json()['items'] == []
    assert client.get(f'/api/profile?user_id={other.pk}').json()['email'] == account_user.email
    response = client.put('/api/profile', dict(user_id=other.pk, name='Changed', email=account_user.email, role='admin'), content_type='application/json')
    assert response.status_code == 200
    other.refresh_from_db()
    account_user.refresh_from_db()
    assert other.name == 'Private'
    assert account_user.role == 'user'


@pytest.mark.parametrize('remember', [False, True])
def test_login_cookie_last_login_and_logout(client, account_user, remember):
    before = timezone.now()
    response = client.post('/api/login', dict(email=account_user.email, password=TEST_PASSWORD, remember=remember), content_type='application/json')
    assert response.status_code == 200
    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert bool(cookie['max-age']) is remember
    assert client.session.get_expire_at_browser_close() is (not remember)
    account_user.refresh_from_db()
    assert account_user.last_login >= before
    session_key = client.session.session_key
    assert account_user.user_sessions.filter(session_token=session_key).exists()
    assert account_user.actions.filter(action='login').count() == 1
    assert client.post('/api/logout').status_code == 200
    assert not Session.objects.filter(session_key=session_key).exists()
    assert account_user.actions.filter(action='logout').count() == 1
    assert client.get('/api/profile').status_code == 401


def test_expired_session_cannot_access_account(client, account_user):
    client.force_login(account_user)
    Session.objects.filter(session_key=client.session.session_key).update(expire_date=timezone.now() - timedelta(seconds=1))
    assert client.get('/api/profile').status_code == 401
    assert client.get('/account.html').status_code == 302


@pytest.mark.parametrize('path,method', [('/api/register','post'), ('/api/login','post'), ('/api/feedback','post'),
    ('/api/profile','put'), ('/api/password','post'), ('/api/cart','put'), ('/api/orders','post'), ('/api/logout','post')])
def test_write_endpoints_reject_missing_or_invalid_csrf(account_user, path, method):
    client = Client(enforce_csrf_checks=True)
    client.force_login(account_user)
    client.get('/tickets.html')
    assert getattr(client, method)(path, {}, content_type='application/json').status_code == 403
    assert getattr(client, method)(path, {}, content_type='application/json', HTTP_X_CSRFTOKEN='x' * 32).status_code == 403


def test_valid_csrf_token_allows_profile_update(account_user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(account_user)
    client.get('/account.html')
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    response = client.put('/api/profile', dict(name='CSRF checked', email=account_user.email),
                          content_type='application/json', HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
    account_user.refresh_from_db()
    assert account_user.name == 'CSRF checked'
