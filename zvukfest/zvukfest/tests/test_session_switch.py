import pytest
from django.conf import settings
from django.contrib.sessions.models import Session

from main.models import User, UserAction, UserSession
from .conftest import TEST_PASSWORD


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('action', ['register', 'login'])
def test_switching_account_saves_new_session(client, account_user, registration_data, action):
    client.force_login(account_user)
    old_key = client.session.session_key
    if action == 'login':
        User.objects.create_user(registration_data['email'], registration_data['username'], TEST_PASSWORD)
        data = {'email': registration_data['email'], 'password': TEST_PASSWORD}
    else:
        data = registration_data

    response = client.post('/api/' + action, data, content_type='application/json')
    assert response.status_code == (201 if action == 'register' else 200)
    new_user = User.objects.get(email=registration_data['email'])
    key = response.cookies[settings.SESSION_COOKIE_NAME].value
    assert key and key != old_key
    assert not Session.objects.filter(session_key=old_key).exists()
    assert Session.objects.get(session_key=key).get_decoded()['_auth_user_id'] == str(new_user.pk)
    assert UserSession.objects.get(session_token=key).user_id == new_user.pk
    assert client.get('/api/profile').json()['email'] == new_user.email
    assert UserAction.objects.filter(user=new_user, action=action).exists()


def test_repeated_login_reuses_tracking_record_and_updates_expiry(client, account_user):
    data = {'email': account_user.email, 'password': TEST_PASSWORD, 'remember': False}
    assert client.post('/api/login', data, content_type='application/json').status_code == 200
    key = client.session.session_key
    data['remember'] = True
    response = client.post('/api/login', data, content_type='application/json')
    assert response.status_code == 200
    assert client.session.session_key == key
    assert UserSession.objects.filter(user=account_user).count() == 1
    assert response.cookies[settings.SESSION_COOKIE_NAME]['max-age']
    assert not client.session.get_expire_at_browser_close()
    assert client.get('/api/profile').status_code == 200


def test_failed_registration_rolls_back_user_and_session(client, registration_data, monkeypatch):
    def fail_logging(*args, **kwargs):
        raise RuntimeError('Simulated action logging failure')

    monkeypatch.setattr('main.views.log_action', fail_logging)
    with pytest.raises(RuntimeError, match='Simulated'):
        client.post('/api/register', registration_data, content_type='application/json')
    assert not User.objects.filter(email=registration_data['email']).exists()
    assert not UserSession.objects.exists()
    assert not Session.objects.exists()
