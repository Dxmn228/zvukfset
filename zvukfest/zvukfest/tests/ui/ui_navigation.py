from pathlib import Path

import pytest
from playwright.sync_api import expect

from main.models import CartItem


MENU = ['index.html', 'program.html', 'artists.html', 'tickets.html', 'account.html', 'cart.html']


def test_navigation_and_document_links(ui_page, live_server):
    ui_page.goto(live_server.url + '/index.html')
    # Visit more than ten actual links, including the cart and both legal pages.
    for filename in ['program.html', 'artists.html', 'tickets.html', 'cart.html', 'index.html',
                     'privacy.html', 'terms.html', 'tickets.html', 'cart.html', 'privacy.html', 'index.html']:
        nav = ui_page.locator('.footer__legal' if filename in ('privacy.html', 'terms.html') else '#main-nav')
        link = nav.locator(f'a[href="{filename}"]')
        if filename == 'privacy.html':
            with ui_page.expect_popup() as popup_info:
                link.click()
            popup = popup_info.value
            expect(popup).to_have_url(live_server.url + '/' + filename)
            expect(popup.locator('main h1')).to_be_visible()
            popup.close()
            continue
        link.click()
        expect(ui_page).to_have_url(live_server.url + '/' + filename)
        expect(ui_page.locator('main h1')).to_be_visible()
        assert ui_page.locator('#main-nav a').evaluate_all('(links) => links.map(a => a.getAttribute("href"))') == MENU


def test_guest_account_and_cart(ui_page, live_server):
    ui_page.goto(live_server.url + '/account.html')
    expect(ui_page).to_have_url(live_server.url + '/tickets.html#login')
    ui_page.locator('#main-nav a[href="cart.html"]').click()
    expect(ui_page.locator('#cart-login')).to_be_visible()
    expect(ui_page.locator('#cart-content')).to_be_hidden()
    ui_page.locator('#cart-login a').click()
    expect(ui_page).to_have_url(live_server.url + '/tickets.html#login')


def test_mobile_menu_works_with_keyboard(ui_page, live_server):
    ui_page.set_viewport_size({'width': 360, 'height': 800})
    ui_page.goto(live_server.url + '/index.html')
    burger = ui_page.locator('.burger')
    expect(ui_page.locator('.nav__list')).to_be_hidden()
    ui_page.keyboard.press('Tab')
    expect(ui_page.locator('.header__logo')).to_be_focused()
    ui_page.keyboard.press('Tab')
    expect(burger).to_be_focused()
    assert burger.evaluate('el => getComputedStyle(el).outlineStyle') != 'none'
    ui_page.keyboard.press('Enter')
    expect(burger).to_have_attribute('aria-expanded', 'true')
    expect(ui_page.locator('.nav__list')).to_be_visible()
    box = burger.bounding_box()
    assert box['width'] >= 44 and box['height'] >= 44
    ui_page.keyboard.press('Escape')
    expect(burger).to_have_attribute('aria-expanded', 'false')
    expect(ui_page.locator('.nav__list')).to_be_hidden()
    burger.click()
    ui_page.locator('#main-nav a[href="tickets.html"]').click()
    expect(ui_page).to_have_url(live_server.url + '/tickets.html')


@pytest.mark.parametrize('width', [360, 768, 1440])
@pytest.mark.parametrize('filename', ['tickets.html', 'cart.html', 'account.html', 'privacy.html'])
def test_responsive_layout(ui_page, live_server, sign_in, registered_user, catalogue, width, filename, pytestconfig, browser_name):
    ui_page.set_viewport_size({'width': width, 'height': 900})
    if filename in ('cart.html', 'account.html'):
        CartItem.objects.create(user=registered_user, product=catalogue[0], quantity=2)
        sign_in()
    ui_page.goto(live_server.url + '/' + filename)
    expect(ui_page.locator('main h1')).to_be_visible()
    if filename == 'tickets.html':
        expect(ui_page.locator('#products-body tr')).to_have_count(3)
    elif filename == 'cart.html':
        expect(ui_page.locator('#cart-clear')).to_be_visible()
    elif filename == 'account.html':
        expect(ui_page.locator('#acc-email')).to_have_value(registered_user.email)
    ui_page.evaluate('document.fonts.ready')
    dimensions = ui_page.evaluate('({page: document.documentElement.scrollWidth, viewport: innerWidth})')
    assert dimensions['page'] <= dimensions['viewport'] + 1, dimensions
    output = Path(pytestconfig.getoption('--output')) / 'layouts' / browser_name
    output.mkdir(parents=True, exist_ok=True)
    ui_page.screenshot(path=str(output / f'{filename}-{width}.png'), full_page=True)
