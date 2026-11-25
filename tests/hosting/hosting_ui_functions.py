import secrets

import pytest
from playwright.sync_api import expect

from hosting_accounts import new_account, record_account

pytestmark = [pytest.mark.browser, pytest.mark.functional, pytest.mark.writes]


@pytest.fixture
def signed_page(hosted_page, account, site_url):
    hosted_page.goto(site_url + '/tickets.html')
    hosted_page.locator('#login-email').fill(account.email)
    hosted_page.locator('#login-password').fill(account.password)
    hosted_page.locator('#login button[type=submit]').click()
    expect(hosted_page).to_have_url(site_url + '/account.html')
    expect(hosted_page.locator('#acc-email')).to_have_value(account.email)
    return hosted_page


def test_registration_in_browser(hosted_page, site_url, request):
    account = new_account(site_url)
    record_account(account, request.node.nodeid)
    hosted_page.goto(site_url + '/tickets.html')
    hosted_page.locator('#reg-username').fill(account.name)
    hosted_page.locator('#reg-email').fill(account.email)
    hosted_page.locator('#reg-password').fill(account.password)
    hosted_page.locator('#reg-password-confirm').fill(account.password)
    hosted_page.locator('#reg-terms').check()
    hosted_page.locator('#reg-privacy').check()
    hosted_page.locator('#register button[type=submit]').click()
    expect(hosted_page).to_have_url(site_url + '/account.html')
    expect(hosted_page.locator('#acc-email')).to_have_value(account.email)
    hosted_page.reload()
    expect(hosted_page.locator('#acc-email')).to_have_value(account.email)
    hosted_page.locator('#logout').click()
    expect(hosted_page).to_have_url(site_url + '/index.html')


def test_profile_password_and_logout_in_browser(signed_page, account, site_url):
    page = signed_page
    page.locator('#acc-name').fill('Hosting UI updated')
    page.locator('#acc-phone').fill('+79990000000')
    page.locator('#profile-form button[type=submit]').click()
    expect(page.locator('#profile-form .form__status')).to_have_text('Профиль сохранён')
    page.reload()
    expect(page.locator('#acc-name')).to_have_value('Hosting UI updated')
    expect(page.locator('#acc-phone')).to_have_value('+79990000000')
    new_password = secrets.token_urlsafe(24)
    page.locator('#acc-old').fill('wrong-password')
    page.locator('#acc-new').fill(new_password)
    page.locator('#acc-confirm').fill(new_password)
    form = page.locator('form[name=password]')
    form.get_by_role('button', name='Изменить пароль').click()
    expect(form.locator('.form__status')).to_contain_text('Неверный текущий пароль')
    page.locator('#acc-old').fill(account.password)
    form.get_by_role('button', name='Изменить пароль').click()
    expect(form.locator('.form__status')).to_have_text('Пароль изменён')
    page.reload()
    expect(page.locator('#acc-email')).to_have_value(account.email)
    page.locator('#logout').click()
    expect(page).to_have_url(site_url + '/index.html')
    page.goto(site_url + '/account.html')
    expect(page).to_have_url(site_url + '/tickets.html#login')
    page.locator('#login-email').fill(account.email)
    page.locator('#login-password').fill(account.password)
    page.locator('#login button[type=submit]').click()
    expect(page.locator('#login .form__status')).to_contain_text('Неверный email или пароль')
    page.locator('#login-password').fill(new_password)
    page.locator('#login button[type=submit]').click()
    expect(page).to_have_url(site_url + '/account.html')


def test_feedback_form_and_safe_rendering(signed_page, account, site_url):
    page = signed_page
    message = 'Hosting UI <b>plain text</b> check'
    page.goto(site_url + '/tickets.html')
    page.locator('#fb-name').fill(account.name)
    page.locator('#fb-email').fill(account.email)
    page.locator('#fb-subject').select_option('tickets')
    page.locator('#fb-message').fill(message)
    page.locator('#fb-privacy').check()
    form = page.locator('#feedback')
    form.locator('button[type=submit]').click()
    expect(form.locator('.form__status')).to_contain_text('Сообщение отправлено')
    expect(page.locator('#fb-message')).to_have_value('')
    page.goto(site_url + '/account.html')
    expect(page.locator('#feedback-list')).to_contain_text(message)
    expect(page.locator('#feedback-list b')).to_have_count(0)


def test_ticket_details_cart_controls_and_demo_order(signed_page, hosted_ticket, site_url):
    page = signed_page
    name = hosted_ticket['name']
    page.goto(site_url + '/tickets.html')
    # Real catalogue names/prices are used; no fixture products are inserted.
    row = page.locator('#products-body tr').filter(has=page.get_by_role('rowheader', name=name, exact=True)).first
    row.get_by_role('button', name='Подробнее: ' + name, exact=True).click()
    expect(page.locator('#ticket-dialog')).to_be_visible()
    expect(page.locator('#ticket-description')).not_to_contain_text('Загружаем')
    expect(page.locator('#ticket-description')).not_to_contain_text('Не удалось')
    page.keyboard.press('Escape')
    row.get_by_role('button', name='В корзину', exact=True).click()
    expect(page.locator('#cart-badge')).to_have_text('1')
    page.goto(site_url + '/cart.html')
    expect(page.locator('#cart-count')).to_have_text('1')
    page.get_by_role('button', name='Увеличить количество: ' + name, exact=True).click()
    expect(page.locator('#cart-count')).to_have_text('2')
    page.reload()
    expect(page.locator('#cart-count')).to_have_text('2')
    page.get_by_role('button', name='Уменьшить количество: ' + name, exact=True).click()
    expect(page.locator('#cart-count')).to_have_text('1')
    page.get_by_role('button', name='Удалить: ' + name, exact=True).click()
    expect(page.locator('#cart-empty')).to_be_visible()
    for clear_only in (True, False):
        page.goto(site_url + '/tickets.html')
        row.get_by_role('button', name='В корзину', exact=True).click()
        expect(page.locator('#cart-badge')).to_have_text('1')
        page.goto(site_url + '/cart.html')
        if clear_only:
            expect(page.locator('#cart-clear')).to_be_enabled()
            page.locator('#cart-clear').click()
        else:
            page.locator('#cart-checkout').click()
            expect(page.locator('#cart-status')).to_contain_text('Учебный заказ №')
        expect(page.locator('#cart-empty')).to_be_visible()
    page.goto(site_url + '/account.html')
    expect(page.locator('#orders-list')).to_contain_text(name)
    page.reload()
    expect(page.locator('#orders-list')).to_contain_text(name)


def test_slider_and_mobile_menu_on_hosted_site(hosted_page, site_url):
    page = hosted_page
    page.set_viewport_size({'width': 360, 'height': 900})
    page.goto(site_url + '/')
    slider = page.locator('.festival-slider')
    expect(slider.locator('[role=status]')).to_have_text('Слайд 1 из 3')
    slider.get_by_role('button', name='Следующий слайд').click()
    expect(slider.locator('[role=status]')).to_have_text('Слайд 2 из 3')
    page.keyboard.press('ArrowRight')
    expect(slider.locator('[role=status]')).to_have_text('Слайд 3 из 3')
    toggle = page.locator('[aria-controls=main-nav]')
    toggle.focus()
    page.keyboard.press('Enter')
    expect(toggle).to_have_attribute('aria-expanded', 'true')
    page.keyboard.press('Escape')
    expect(toggle).to_have_attribute('aria-expanded', 'false')
