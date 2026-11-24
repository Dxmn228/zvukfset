import pytest

from main.models import Feedback, Product

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('change,field', [({'subject': 'invalid'}, 'subject'),
    ({'message': 'short'}, 'message'), ({'message': 'x' * 2001}, 'message'),
    ({'rating': 0}, 'rating'), ({'rating': 6}, 'rating'), ({'rating': 1.5}, 'rating'),
    ({'email': 'invalid'}, 'email'), ({'privacy': False}, 'privacy')])
def test_invalid_feedback_is_not_saved(client, account_user, change, field):
    client.force_login(account_user)
    data = dict(name='Test', email=account_user.email, subject='tickets', message='Valid long message', rating=5, privacy=True)
    response = client.post('/api/feedback', {**data, **change}, content_type='application/json')
    assert response.status_code == 400
    assert field in response.json()['errors']
    assert not Feedback.objects.exists()
    assert not account_user.actions.filter(action='send_feedback').exists()


def test_search_history_and_viewed_items_are_bounded_and_persist(client, account_user):
    client.force_login(account_user)
    products = [Product.objects.create(name=f'Ticket {i}', alias=f'ticket-{i}', short_description='Music', description='Special admission', price=100) for i in range(7)]
    for i, product in enumerate(products):
        assert client.get('/api/search', {'q': f'Ticket {i}'}).status_code == 200
        assert client.get(f'/api/products/{product.pk}').status_code == 200
    client.get('/api/search', {'q': 'Ticket 4'})
    client.get(f'/api/products/{products[4].pk}')
    actions = client.get('/api/actions').json()
    assert actions['search_history'] == ['Ticket 4', 'Ticket 6', 'Ticket 5', 'Ticket 3', 'Ticket 2']
    assert [p['id'] for p in actions['last_viewed']] == [products[i].pk for i in [4, 6, 5, 3, 2]]
    assert len(client.get('/api/search', {'q': 'Special admission'}).json()['items']) == 7
    assert account_user.actions.filter(action='search').count() == 9
    assert account_user.actions.filter(action='view_product').count() == 8


@pytest.mark.parametrize('query', ['', 'x', 'x' * 101])
def test_invalid_search_not_recorded(client, account_user, query):
    client.force_login(account_user)
    assert client.get('/api/search', {'q': query}).status_code == 400
    assert client.session.get('search_history', []) == []


def test_sql_like_search_is_treated_as_text(client, ticket_product):
    response = client.get('/api/search', {'q': "' OR 1=1 --"})
    assert response.status_code == 200
    assert response.json()['items'] == []
    assert Product.objects.filter(pk=ticket_product.pk).exists()
