from playwright.sync_api import expect

from main.models import CartItem


def test_search_and_sold_out_ticket(ui_page, live_server, catalogue):
    ui_page.goto(live_server.url + '/tickets.html')
    rows = ui_page.locator('#products-body .ticket-product')
    expect(rows).to_have_count(3)
    expect(ui_page.get_by_role('button', name='Распродано', exact=True)).to_be_disabled()
    search = ui_page.locator('.search-form')
    ui_page.locator('#search-query').fill('VIP')
    search.get_by_role('button', name='Найти', exact=True).click()
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text('VIP-билет')
    ui_page.locator('#search-query').fill('Несуществующий билет')
    search.get_by_role('button', name='Найти', exact=True).click()
    expect(ui_page.locator('#products-body tr').first).to_contain_text('По вашему запросу билеты не найдены')
    ui_page.locator('#search-query').fill('')
    search.get_by_role('button', name='Найти', exact=True).click()
    expect(rows).to_have_count(3)


def test_catalogue_error_can_be_retried(ui_page, live_server, catalogue):
    pattern = '**/api/products?*'
    ui_page.route(pattern, lambda route: route.fulfill(status=503, json={'error': 'Test failure'}))
    ui_page.goto(live_server.url + '/tickets.html')
    retry = ui_page.get_by_role('button', name='Повторить загрузку')
    expect(retry).to_be_visible()
    ui_page.unroute(pattern)
    retry.click()
    expect(ui_page.locator('#products-body .ticket-product')).to_have_count(3)


def test_all_permanent_tickets_are_grouped_by_artist_and_have_images(ui_page, live_server):
    from django.core.management import call_command

    call_command('bootstrap_catalog')
    ui_page.goto(live_server.url + '/tickets.html')
    expect(ui_page.locator('#products-body .ticket-category')).to_have_count(4)
    expect(ui_page.locator('#products-body .ticket-product')).to_have_count(8)
    expect(ui_page.locator('#products-body .ticket-product img.ticket-image')).to_have_count(8)

    expected = {
        'Шаман': ('пятница, 16 июля 2027 г.', '18:00'),
        'Ваня Дмитриенко': ('пятница, 16 июля 2027 г.', '19:30'),
        'Стас Михайлов': ('пятница, 16 июля 2027 г.', '21:00'),
        'Анна Асти': ('пятница, 16 июля 2027 г.', '22:30'),
    }
    for artist, values in expected.items():
        category = ui_page.locator('.ticket-category').filter(has_text=artist)
        expect(category).to_have_count(1)
        expect(category).not_to_contain_text('цена выступления')
        for value in values:
            expect(category).to_contain_text(value)

    for alias in ('shaman', 'vanya', 'stas', 'anna'):
        assert ui_page.locator(f'.ticket-product img[src="/img/{alias}.jpg"]').count() == 2


def test_cart_add_change_remove_and_clear(signed_in_page, live_server, catalogue):
    page = signed_in_page
    page.goto(live_server.url + '/tickets.html')
    for name in ('Обычный билет', 'VIP-билет'):
        row = page.locator('#products-body tr').filter(has=page.get_by_role('rowheader', name=name, exact=True))
        row.get_by_role('button', name='В корзину', exact=True).click()
        expect(page.locator('.search-form .form__status')).to_contain_text('Билет добавлен')
    page.locator('#main-nav a[href="cart.html"]').click()
    expect(page.locator('#cart-count')).to_have_text('2')
    assert total(page) == '1567,00₽'
    standard = page.locator('.cart-item').filter(has=page.get_by_role('heading', name='Обычный билет', exact=True))
    expect(standard.get_by_role('button', name='Уменьшить количество: Обычный билет', exact=True)).to_be_disabled()
    standard.get_by_role('button', name='Увеличить количество: Обычный билет', exact=True).click()
    expect(page.locator('#cart-count')).to_have_text('3')
    expect(page.locator('#cart-clear')).to_be_enabled()
    assert total(page) == '1634,00₽'
    page.reload()
    expect(page.locator('#cart-count')).to_have_text('3')
    page.get_by_role('button', name='Удалить: VIP-билет', exact=True).click()
    expect(page.locator('#cart-count')).to_have_text('2')
    expect(page.locator('#cart-clear')).to_be_enabled()
    page.locator('#cart-clear').click()
    expect(page.locator('#cart-empty')).to_be_visible()
    expect(page.locator('#cart-content')).to_be_hidden()
    page.reload()
    expect(page.locator('#cart-empty')).to_be_visible()
    assert CartItem.objects.count() == 0


def total(page):
    return ''.join(page.locator('#cart-total').inner_text().split())


def test_cart_limit_and_failed_save_restore_controls(signed_in_page, live_server, registered_user, catalogue):
    page = signed_in_page
    CartItem.objects.create(user=registered_user, product=catalogue[0], quantity=20)
    page.goto(live_server.url + '/cart.html')
    expect(page.locator('#cart-count')).to_have_text('20')
    plus = page.get_by_role('button', name='Увеличить количество: Обычный билет', exact=True)
    expect(plus).to_be_disabled()

    def fail_write(route):
        if route.request.method == 'PUT':
            route.fulfill(status=503, json={'error': 'Не удалось сохранить корзину.'})
        else:
            route.continue_()

    page.route('**/api/cart', fail_write)
    page.locator('#cart-clear').click()
    expect(page.locator('#cart-status')).to_have_text('Не удалось сохранить корзину.')
    expect(page.locator('#cart-clear')).to_be_enabled()
    expect(plus).to_be_disabled()
    expect(page.locator('#cart-count')).to_have_text('20')
    page.unroute('**/api/cart')
    page.locator('#cart-clear').click()
    expect(page.locator('#cart-empty')).to_be_visible()
