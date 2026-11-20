from playwright.sync_api import expect

from main.models import Feedback, User


def fill_registration(page):
    page.locator('#reg-username').fill('Новый зритель')
    page.locator('#reg-email').fill('new-browser@example.com')
    page.locator('#reg-password').fill('New-browser-password-123')
    page.locator('#reg-password-confirm').fill('New-browser-password-123')


def test_registration_and_document_popups(ui_page, live_server):
    ui_page.goto(live_server.url + '/tickets.html')
    fill_registration(ui_page)
    for name, title in [('terms', 'Пользовательское соглашение'), ('privacy', 'Политика конфиденциальности')]:
        checkbox = ui_page.locator('#reg-' + name)
        expect(checkbox).not_to_be_checked()
        with ui_page.expect_popup() as popup_info:
            ui_page.locator(f'label[for="reg-{name}"] a').click()
        popup = popup_info.value
        expect(popup.locator('h1')).to_have_text(title)
        popup.close()
        expect(checkbox).not_to_be_checked()
        expect(ui_page.locator('#reg-email')).to_have_value('new-browser@example.com')
        checkbox.check()
    ui_page.locator('#register button[type="submit"]').click()
    expect(ui_page).to_have_url(live_server.url + '/account.html')
    expect(ui_page.locator('#acc-email')).to_have_value('new-browser@example.com')
    user = User.objects.get(email='new-browser@example.com')
    assert user.check_password('New-browser-password-123')


def test_registration_validation_blocks_submission(ui_page, live_server):
    ui_page.goto(live_server.url + '/tickets.html')
    requests = []
    ui_page.on('request', lambda r: requests.append(r.url) if r.url.endswith('/api/register') else None)
    fill_registration(ui_page)
    form = ui_page.locator('#register')
    form.locator('button[type="submit"]').click()
    assert ui_page.locator('#reg-terms').evaluate('el => el.validity.valueMissing')
    ui_page.locator('#reg-terms').check()
    form.locator('button[type="submit"]').click()
    assert ui_page.locator('#reg-privacy').evaluate('el => el.validity.valueMissing')
    ui_page.locator('#reg-privacy').check()
    ui_page.locator('#reg-password-confirm').fill('different-password')
    form.locator('button[type="submit"]').click()
    assert ui_page.locator('#reg-password-confirm').evaluate('el => el.validity.customError')
    ui_page.locator('#reg-password-confirm').fill('New-browser-password-123')
    ui_page.locator('#reg-email').fill('invalid-email')
    form.locator('button[type="submit"]').click()
    assert ui_page.locator('#reg-email').evaluate('el => el.validity.typeMismatch')
    assert requests == []


def test_wrong_password_shows_error(ui_page, live_server, registered_user):
    ui_page.goto(live_server.url + '/tickets.html')
    ui_page.locator('#login-email').fill(registered_user.email)
    ui_page.locator('#login-password').fill('wrong-password')
    ui_page.locator('#login button[type="submit"]').click()
    expect(ui_page.locator('#login .form__status')).to_have_text('Неверный email или пароль')
    expect(ui_page.locator('#login button[type="submit"]')).to_be_enabled()


def test_profile_edit_and_logout(signed_in_page, live_server):
    page = signed_in_page
    page.locator('#acc-name').fill('Изменённое имя')
    page.locator('#acc-phone').fill('+79990000000')
    page.locator('#profile-form button[type="submit"]').click()
    expect(page.locator('#profile-form .form__status')).to_have_text('Профиль сохранён')
    page.reload()
    expect(page.locator('#acc-name')).to_have_value('Изменённое имя')
    expect(page.locator('#acc-phone')).to_have_value('+79990000000')
    page.locator('#logout').click()
    expect(page).to_have_url(live_server.url + '/index.html')
    page.goto(live_server.url + '/account.html')
    expect(page).to_have_url(live_server.url + '/tickets.html#login')


def test_feedback_is_sent_and_form_resets(ui_page, live_server):
    ui_page.goto(live_server.url + '/tickets.html')
    ui_page.locator('#fb-name').fill('Тестовый зритель')
    ui_page.locator('#fb-email').fill('feedback@example.com')
    ui_page.locator('#fb-subject').select_option('tickets')
    ui_page.locator('#fb-message').fill('Подскажите время открытия фестиваля.')
    ui_page.locator('#fb-privacy').check()
    form = ui_page.locator('form[name="feedback"]')
    form.locator('button[type="submit"]').click()
    expect(form.locator('.form__status')).to_have_text('Спасибо! Сообщение отправлено.')
    expect(ui_page.locator('#fb-message')).to_have_value('')
    assert Feedback.objects.filter(email='feedback@example.com').count() == 1


def test_account_network_error_is_reported(signed_in_page):
    page = signed_in_page
    page.route('**/api/actions', lambda route: route.abort('failed'))
    page.reload()
    expect(page.locator('#account-info')).to_contain_text('Не удалось загрузить данные личного кабинета')
    page.unroute('**/api/actions')
    page.reload()
    expect(page.locator('#search-list li').first).to_be_visible()
    expect(page.locator('#account-info')).not_to_contain_text('Не удалось загрузить')
