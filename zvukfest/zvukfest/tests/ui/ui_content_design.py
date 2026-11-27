import re

import pytest
from playwright.sync_api import expect


PUBLIC_HEROES = (
    pytest.param('tickets.html', 'Билеты', '16 июля 2027 · Парк Горького', id='tickets'),
    pytest.param('artists.html', 'Артисты', 'Главная сцена · 16 июля 2027', id='artists'),
    pytest.param('cart.html', 'Корзина', 'Ваш выбор', id='cart'),
    pytest.param('privacy.html', 'Политика конфиденциальности', 'Документы сайта', id='privacy'),
    pytest.param('terms.html', 'Пользовательское соглашение', 'Документы сайта', id='terms'),
)


@pytest.mark.parametrize(('filename', 'title', 'eyebrow'), PUBLIC_HEROES)
def test_public_pages_use_shared_festival_hero(ui_page, live_server, filename, title, eyebrow):
    ui_page.goto(f'{live_server.url}/{filename}')
    hero = ui_page.locator('.page-hero')
    expect(hero).to_be_visible()
    expect(hero.get_by_role('heading', level=1)).to_have_text(title)
    expect(hero.locator('.page-hero__eyebrow')).to_have_text(eyebrow)
    styles = hero.evaluate('''element => {
        const style = getComputedStyle(element);
        return {background: style.backgroundColor, radius: parseFloat(style.borderRadius)};
    }''')
    assert styles['background'] == 'rgb(25, 26, 35)'
    assert styles['radius'] > 0


def test_homepage_keeps_matching_festival_hero(ui_page, live_server):
    ui_page.goto(live_server.url + '/index.html')
    hero = ui_page.locator('.festival-hero')
    expect(hero).to_be_visible()
    expect(hero.get_by_role('heading', name='Звук Фест')).to_be_visible()
    expect(hero.get_by_role('link', name='Смотреть программу')).to_have_attribute('href', 'program.html')
    expect(hero.get_by_role('link', name='Выбрать билет')).to_have_attribute('href', 'tickets.html')


def test_program_contains_day_facts_lineup_spaces_and_call_to_action(ui_page, live_server):
    ui_page.goto(live_server.url + '/program.html')
    hero = ui_page.locator('.program-hero')
    expect(hero).to_be_visible()
    expect(hero.get_by_role('heading', name='Программа фестиваля')).to_be_visible()
    expect(hero.locator('.program-hero__eyebrow')).to_have_text('16 июля 2027 · Москва')

    facts = ui_page.locator('.program-fact')
    expect(facts).to_have_count(3)
    assert facts.locator('.program-fact__value').all_text_contents() == ['15:00', '18:00', '4']
    assert facts.get_by_role('heading').all_text_contents() == [
        'Открытие входа', 'Старт выступлений', 'Артиста за вечер',
    ]

    slots = ui_page.locator('.program-slot')
    expect(slots).to_have_count(4)
    assert slots.locator('time').all_text_contents() == ['18:00', '19:30', '21:00', '22:30']
    assert slots.get_by_role('heading').all_text_contents() == [
        'Шаман', 'Ваня Дмитриенко', 'Стас Михайлов', 'Анна Асти',
    ]
    expect(slots.get_by_role('link', name=re.compile('Билеты'))).to_have_count(4)

    spaces = ui_page.locator('.program-spaces li')
    expect(spaces).to_have_count(3)
    assert spaces.get_by_role('heading').all_text_contents() == [
        'Фуд-корт', 'Зона отдыха', 'Мерч и фотозона',
    ]
    note = ui_page.locator('.program-note')
    expect(note.get_by_role('heading', name='Полезно знать')).to_be_visible()
    expect(note.get_by_role('link', name='Купить билет')).to_have_attribute('href', 'tickets.html')

    hero.get_by_role('link', name='Смотреть расписание').click()
    expect(ui_page).to_have_url(re.compile(r'/program\.html#lineup$'))
    expect(ui_page.locator('#lineup')).to_be_in_viewport()


def test_artist_cards_show_photo_schedule_description_and_ticket_link(ui_page, live_server):
    ui_page.goto(live_server.url + '/artists.html')
    cards = ui_page.locator('.artist')
    expect(cards).to_have_count(4)
    expected = (
        ('Шаман', '18:00'),
        ('Ваня Дмитриенко', '19:30'),
        ('Стас Михайлов', '21:00'),
        ('Анна Асти', '22:30'),
    )
    for index, (artist, time) in enumerate(expected):
        card = cards.nth(index)
        expect(card.get_by_role('heading', name=artist, exact=True)).to_be_visible()
        expect(card.locator('.artist__time')).to_contain_text(time)
        expect(card.locator('.artist__time')).to_contain_text('Главная сцена')
        expect(card.locator('.artist__text')).not_to_be_empty()
        expect(card.get_by_role('link', name='Выбрать билет')).to_have_attribute('href', 'tickets.html')
        assert card.locator('.artist__photo').evaluate('image => image.complete && image.naturalWidth > 0')


def test_account_has_hero_profile_activity_and_order_panels(signed_in_page):
    page = signed_in_page
    hero = page.locator('.page-hero')
    expect(hero.get_by_role('heading', name='Личный кабинет')).to_be_visible()
    expect(hero.locator('#account-info')).to_contain_text('Роль: пользователь')
    expect(hero.get_by_role('button', name='Выйти')).to_be_visible()

    expect(page.locator('#profile-form')).to_be_visible()
    expect(page.locator('form[name="password"]')).to_be_visible()
    activity = page.locator('.account-activity .account-card')
    expect(activity).to_have_count(3)
    assert activity.get_by_role('heading').all_text_contents() == [
        'Журнал действий', 'Просмотренные билеты', 'История поиска',
    ]
    expect(page.locator('.account-panel').get_by_role('heading', name='Мои обращения')).to_be_visible()
    expect(page.locator('#orders').get_by_role('heading', name='История заказов')).to_be_visible()


@pytest.mark.parametrize(('filename', 'section_count'), (
    pytest.param('privacy.html', 6, id='privacy'),
    pytest.param('terms.html', 6, id='terms'),
))
def test_legal_pages_have_status_contents_and_readable_sections(
        ui_page, live_server, filename, section_count):
    ui_page.goto(f'{live_server.url}/{filename}')
    document = ui_page.locator('.legal-page')
    expect(document.locator('.legal-page__notice')).to_contain_text('Учебный проект')
    expect(document.locator('.legal-page__contents li')).to_have_count(section_count)
    expect(document.locator(':scope > section')).to_have_count(section_count)
    assert document.locator(':scope > section h2').all_text_contents()


def test_ticket_page_hero_links_program_and_catalogue_uses_cards(ui_page, live_server, catalogue):
    ui_page.goto(live_server.url + '/tickets.html')
    hero = ui_page.locator('.page-hero')
    expect(hero.get_by_role('link', name='Посмотреть программу')).to_have_attribute(
        'href', 'program.html#lineup')
    expect(ui_page.locator('#products-body .ticket-product')).to_have_count(3)
    expect(ui_page.locator('#products-body table')).to_have_count(0)


def test_cart_page_has_shared_hero_and_guest_state(ui_page, live_server):
    ui_page.goto(live_server.url + '/cart.html')
    expect(ui_page.locator('.page-hero').get_by_role('heading', name='Корзина')).to_be_visible()
    expect(ui_page.locator('#cart-login')).to_be_visible()
    expect(ui_page.locator('#cart-login').get_by_role(
        'link', name='Войти или зарегистрироваться')).to_have_attribute('href', 'tickets.html#login')
