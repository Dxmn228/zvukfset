import pytest

from main.models import Category, Feedback, Product, ProductImage, ProductProperty, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(client):
    admin = User.objects.create_superuser('admin@example.com', 'Test admin', 'Admin-test-password-123')
    client.force_login(admin)
    return client


@pytest.mark.parametrize('signed_in', [False, True])
def test_admin_denies_guest_and_regular_user(client, account_user, ticket_product, signed_in):
    if signed_in:
        client.force_login(account_user)
    paths = ['/admin/', '/admin/main/user/', '/admin/main/feedback/',
             '/admin/main/product/add/', f'/admin/main/product/{ticket_product.pk}/change/']
    for path in paths:
        response = client.get(path)
        assert response.status_code == 302
        assert response.url.startswith('/admin/login/')
    assert client.post(f'/admin/main/product/{ticket_product.pk}/delete/', {'post': 'yes'}).status_code == 302
    assert Product.objects.filter(pk=ticket_product.pk).exists()


def product_form(category, product=None):
    data = dict(name='Admin ticket', alias='admin-ticket', manufacturer_id=1,
                short_description='Admission', description='Full description', price='250.00',
                discount_percent=10, available='on', categories=[str(category.pk)], image='img/main-stage.jpg')
    for prefix in ['properties', 'images']:
        data.update({f'{prefix}-TOTAL_FORMS': '1', f'{prefix}-INITIAL_FORMS': '1' if product else '0',
                     f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000'})
    data.update({'properties-0-property_name': 'Day', 'properties-0-property_value': 'Saturday',
                 'properties-0-property_price': '0.00', 'images-0-image': 'img/main-stage.jpg', 'images-0-title': 'Stage'})
    if product:
        data.update({'properties-0-id': product.properties.get().pk, 'properties-0-product': product.pk,
                     'images-0-id': product.images.get().pk, 'images-0-product': product.pk})
    return data


def test_admin_product_category_and_inline_crud(staff_client):
    response = staff_client.post('/admin/main/category/add/', {'name': 'Tickets', 'alias': 'tickets'})
    assert response.status_code == 302
    category = Category.objects.get(alias='tickets')
    response = staff_client.post('/admin/main/product/add/', product_form(category))
    assert response.status_code == 302
    product = Product.objects.get(alias='admin-ticket')
    assert list(product.categories.all()) == [category]
    assert product.properties.get().property_value == 'Saturday'
    assert product.images.get().title == 'Stage'
    data = product_form(category, product)
    data.update(price='500.00', discount_percent=25)
    data['properties-0-property_value'] = 'Sunday'
    data['images-0-title'] = 'New stage'
    assert staff_client.post(f'/admin/main/product/{product.pk}/change/', data).status_code == 302
    product.refresh_from_db()
    assert product.price == 500 and product.discount_percent == 25
    assert product.properties.get().property_value == 'Sunday'
    assert product.images.get().title == 'New stage'
    invalid = {**data, 'discount_percent': 101}
    response = staff_client.post(f'/admin/main/product/{product.pk}/change/', invalid)
    assert response.status_code == 200
    assert 'discount_percent' in response.context['adminform'].form.errors
    product.refresh_from_db()
    assert product.discount_percent == 25
    assert staff_client.post(f'/admin/main/product/{product.pk}/delete/', {'post': 'yes'}).status_code == 302
    assert not Product.objects.exists()
    assert not ProductProperty.objects.exists()
    assert not ProductImage.objects.exists()
    assert Category.objects.filter(pk=category.pk).exists()
    assert staff_client.post(f'/admin/main/category/{category.pk}/delete/', {'post': 'yes'}).status_code == 302
    assert not Category.objects.exists()


def test_admin_sort_search_filter_and_moderation(staff_client, account_user):
    for name, price in [('Cheap', 10), ('Expensive', 100), ('Middle', 50)]:
        Product.objects.create(name=name, alias=name.lower(), price=price, short_description='Test')
    response = staff_client.get('/admin/main/product/', {'o': '2'})
    assert [p.price for p in response.context['cl'].queryset] == [10, 50, 100]
    response = staff_client.get('/admin/main/product/', {'o': '-2'})
    assert [p.price for p in response.context['cl'].queryset] == [100, 50, 10]
    response = staff_client.get('/admin/main/product/', {'q': 'Cheap'})
    assert [p.name for p in response.context['cl'].queryset] == ['Cheap']
    Product.objects.filter(name='Cheap').update(available=False)
    response = staff_client.get('/admin/main/product/', {'available__exact': '0'})
    assert [p.name for p in response.context['cl'].queryset] == ['Cheap']
    feedback = Feedback.objects.create(user=account_user, name='Test', email=account_user.email, subject='tickets', message='Question about tickets')
    for action, status in [('take_to_work', 'in_progress'), ('mark_resolved', 'resolved')]:
        response = staff_client.post('/admin/main/feedback/', {'action': action, '_selected_action': [feedback.pk], 'index': 0})
        assert response.status_code == 302
        feedback.refresh_from_db()
        assert feedback.status == status


def test_admin_can_edit_user_without_changing_password(staff_client, account_user):
    original_hash = account_user.password
    response = staff_client.post(f'/admin/main/user/{account_user.pk}/change/',
                                dict(name='Edited', email='edited@example.com', phone='', role='user'))
    assert response.status_code == 302
    account_user.refresh_from_db()
    assert account_user.name == 'Edited'
    assert account_user.email == 'edited@example.com'
    assert account_user.password == original_hash
