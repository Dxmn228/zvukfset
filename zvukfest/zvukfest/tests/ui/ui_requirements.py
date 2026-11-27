from playwright.sync_api import expect

from main.models import Order


def test_slider_cycles_with_keyboard(ui_page, live_server):
    ui_page.goto(live_server.url + '/')
    slider = ui_page.locator('.festival-slider')
    expect(slider.locator('.festival-slide:visible')).to_have_count(1)
    expect(slider.locator('[role="status"]')).to_have_text('Слайд 1 из 3')
    slider.get_by_role('button', name='Следующий слайд').click()
    expect(slider.locator('[role="status"]')).to_have_text('Слайд 2 из 3')
    ui_page.keyboard.press('ArrowRight')
    expect(slider.locator('[role="status"]')).to_have_text('Слайд 3 из 3')
    ui_page.keyboard.press('ArrowRight')
    expect(slider.locator('[role="status"]')).to_have_text('Слайд 1 из 3')


def test_policy_download(ui_page, live_server):
    ui_page.goto(live_server.url + '/privacy.html')
    with ui_page.expect_download() as download:
        ui_page.get_by_role('link', name='Скачать политику (.txt)').click()
    assert download.value.suggested_filename == 'privacy-policy.txt'
    assert download.value.failure() is None


def test_details_cart_popup_cache_and_order(signed_in_page, live_server, catalogue, registered_user):
    page = signed_in_page
    catalogue[0].discount_percent = 10
    catalogue[0].save()
    page.goto(live_server.url + '/tickets.html')
    page.get_by_role('button', name='Подробнее: Обычный билет', exact=True).click()
    expect(page.locator('#ticket-description')).to_contain_text('Один день фестиваля')
    page.keyboard.press('Escape')
    card = page.locator('#products-body .ticket-product').filter(
        has=page.get_by_role('heading', name='Обычный билет', exact=True))
    card.get_by_role('button', name='В корзину', exact=True).click()
    expect(page.locator('#cart-badge')).to_have_text('1')
    cached = page.evaluate('(id) => JSON.parse(localStorage.getItem(`zvukfest.cart.${id}`))', registered_user.pk)
    assert cached['total'] == '60.30'
    page.locator('#cart-open').click()
    expect(page.locator('#mini-cart-totals')).to_contain_text('60,30')
    page.get_by_role('button', name='Удалить из окна корзины: Обычный билет', exact=True).click()
    expect(page.locator('#cart-badge')).to_have_text('0')
    page.keyboard.press('Escape')
    card.get_by_role('button', name='В корзину', exact=True).click()
    expect(page.locator('#cart-badge')).to_have_text('1')
    page.goto(live_server.url + '/cart.html')
    expect(page.locator('#cart-count')).to_have_text('1')
    page.locator('#cart-checkout').click()
    expect(page.locator('#cart-status')).to_contain_text('Учебный заказ №')
    expect(page.locator('#cart-empty')).to_be_visible()
    assert Order.objects.filter(user=registered_user).count() == 1
    page.locator('#cart-status a').click()
    expect(page.locator('#orders-list')).to_contain_text('60.30')
    expect(page.locator('#viewed-list')).to_contain_text('Обычный билет')
    page.reload()
    expect(page.locator('#orders-list')).to_contain_text('Обычный билет')
    page.locator('#logout').click()
    expect(page).to_have_url(live_server.url + '/index.html')
    assert page.evaluate('Object.keys(localStorage).filter(k => k.startsWith("zvukfest.cart."))') == []
