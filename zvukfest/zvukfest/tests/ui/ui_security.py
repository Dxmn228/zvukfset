from playwright.sync_api import expect

def test_password_change_errors_and_new_login(signed_in_page, registered_user, live_server, browser_test_password):
    page = signed_in_page
    form = page.locator('form[name="password"]')
    page.locator('#acc-old').fill('wrong-password')
    page.locator('#acc-new').fill('New-ui-password-456')
    page.locator('#acc-confirm').fill('New-ui-password-456')
    form.get_by_role('button', name='Изменить пароль').click()
    expect(form.locator('.form__status')).to_contain_text('Неверный текущий пароль')
    page.locator('#acc-old').fill(browser_test_password)
    page.locator('#acc-confirm').fill('different-password')
    form.get_by_role('button', name='Изменить пароль').click()
    expect(form.locator('.form__status')).to_contain_text('Пароли не совпадают')
    page.locator('#acc-confirm').fill('New-ui-password-456')
    form.get_by_role('button', name='Изменить пароль').click()
    expect(form.locator('.form__status')).to_have_text('Пароль изменён')
    page.reload()
    expect(page.locator('#acc-email')).to_have_value(registered_user.email)
    page.locator('#logout').click()
    expect(page).to_have_url(live_server.url + '/index.html')
    page.goto(live_server.url + '/tickets.html')
    page.locator('#login-email').fill(registered_user.email)
    page.locator('#login-password').fill(browser_test_password)
    page.locator('#login button[type="submit"]').click()
    expect(page.locator('#login .form__status')).to_contain_text('Неверный email или пароль')
    page.locator('#login-password').fill('New-ui-password-456')
    page.locator('#login button[type="submit"]').click()
    expect(page).to_have_url(live_server.url + '/account.html')
    expect(page.locator('#acc-email')).to_have_value(registered_user.email)


def test_stored_markup_is_text_in_catalogue_cart_and_feedback(signed_in_page, catalogue, registered_user, live_server):
    page = signed_in_page
    payload = '<img src=x onerror="window.__xssExecuted=true">'
    page.context.add_init_script('window.__xssExecuted = false')
    catalogue[0].name = payload
    catalogue[0].description = payload
    catalogue[0].save()
    page.goto(live_server.url + '/tickets.html')
    row = page.locator('#products-body tr').filter(has=page.get_by_role('rowheader', name=payload, exact=True))
    expect(row).to_be_visible()
    expect(row.locator('img')).to_have_count(1)
    expect(row.locator('img')).to_have_attribute('src', '/img/ticket.svg')
    row.get_by_role('button', name='Подробнее: ' + payload, exact=True).click()
    expect(page.locator('#ticket-description')).to_have_text(payload)
    expect(page.locator('#ticket-description img')).to_have_count(1)
    expect(page.locator('#ticket-description img')).to_have_attribute('src', '/img/ticket.svg')
    page.keyboard.press('Escape')
    row.get_by_role('button', name='В корзину', exact=True).click()
    expect(page.locator('#cart-badge')).to_have_text('1')
    page.locator('#fb-name').fill('Test')
    page.locator('#fb-email').fill(registered_user.email)
    page.locator('#fb-subject').select_option('tickets')
    page.locator('#fb-message').fill(payload)
    page.locator('#fb-privacy').check()
    form = page.locator('form[name="feedback"]')
    form.locator('button[type="submit"]').click()
    expect(form.locator('.form__status')).to_contain_text('Сообщение отправлено')
    assert page.evaluate('window.__xssExecuted') is False
    page.goto(live_server.url + '/cart.html')
    expect(page.locator('#cart-items h3')).to_have_text(payload)
    expect(page.locator('#cart-items img')).to_have_count(1)
    expect(page.locator('#cart-items img')).to_have_attribute('src', '/img/ticket.svg')
    assert page.evaluate('window.__xssExecuted') is False
    page.goto(live_server.url + '/account.html')
    expect(page.locator('#feedback-list')).to_contain_text(payload)
    expect(page.locator('#feedback-list img')).to_have_count(0)
    assert page.evaluate('window.__xssExecuted') is False
