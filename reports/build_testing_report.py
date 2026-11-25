"""Build a Word report from recorded test evidence (standard-library OOXML)."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ET.register_namespace('w', W)


def el(name, attrs=None, text=None):
    node = ET.Element(f'{{{W}}}{name}', {f'{{{W}}}{k}': str(v) for k, v in (attrs or {}).items()})
    if text is not None:
        node.text = text
    return node


document = el('document')
body = ET.SubElement(document, f'{{{W}}}body')
plain = []


def paragraph(text, style=None, centered=False, code=False):
    p = el('p')
    prop = el('pPr')
    if style:
        prop.append(el('pStyle', {'val': style}))
    if centered:
        prop.append(el('jc', {'val': 'center'}))
        prop.append(el('ind', {'firstLine': 0}))
    if code:
        prop.append(el('ind', {'firstLine': 0}))
        prop.append(el('spacing', {'line': 240, 'lineRule': 'auto', 'after': 80}))
    p.append(prop)
    run = el('r')
    if code:
        rp = el('rPr')
        rp.append(el('rFonts', {'ascii': 'Consolas', 'hAnsi': 'Consolas'}))
        rp.append(el('sz', {'val': 19}))
        run.append(rp)
    t = el('t', text=text)
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    run.append(t)
    p.append(run)
    body.append(p)
    plain.append(text)
    return p


def page_break():
    p = el('p')
    r = el('r')
    r.append(el('br', {'type': 'page'}))
    p.append(r)
    body.append(p)
    plain.append('')


def heading(text, level=1, new_page=False):
    if new_page:
        page_break()
    paragraph(text, f'Heading{level}')


def table(headers, rows, widths=None):
    tbl = el('tbl')
    props = el('tblPr')
    props.append(el('tblW', {'w': 0, 'type': 'auto'}))
    borders = el('tblBorders')
    for name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        borders.append(el(name, {'val': 'single', 'sz': 4, 'color': '888888'}))
    props.append(borders)
    tbl.append(props)
    widths = widths or [int(9300 / len(headers))] * len(headers)
    grid = el('tblGrid')
    for width in widths:
        grid.append(el('gridCol', {'w': width}))
    tbl.append(grid)
    for i, row in enumerate([headers, *rows]):
        tr = el('tr')
        trprop = el('trPr')
        trprop.append(el('cantSplit'))
        if i == 0:
            trprop.append(el('tblHeader'))
        tr.append(trprop)
        for value, width in zip(row, widths):
            tc = el('tc')
            tcp = el('tcPr')
            tcp.append(el('tcW', {'w': width, 'type': 'dxa'}))
            if i == 0:
                tcp.append(el('shd', {'fill': 'E8EEF3'}))
            tc.append(tcp)
            p = el('p')
            pp = el('pPr')
            pp.append(el('ind', {'firstLine': 0}))
            pp.append(el('jc', {'val': 'left'}))
            pp.append(el('spacing', {'line': 240, 'lineRule': 'auto', 'after': 60}))
            p.append(pp)
            r = el('r')
            rp = el('rPr')
            rp.append(el('sz', {'val': 21}))
            if i == 0:
                rp.append(el('b'))
            r.append(rp)
            r.append(el('t', text=str(value)))
            p.append(r)
            tc.append(p)
            tr.append(tc)
        tbl.append(tr)
    body.append(tbl)
    plain.append(' | '.join(headers))
    plain.extend(' | '.join(str(v) for v in row) for row in rows)
    paragraph('')


def suite(name):
    root = ET.parse(ROOT / 'artifacts' / 'hosting' / name).getroot()
    s = next(root.iter('testsuite'))
    return {k: int(s.get(k, 0)) for k in ('tests', 'failures', 'errors', 'skipped')}


api, checks, ui = (suite(n) for n in ('api-results.xml', 'checks-results.xml', 'ui-results.xml'))
load10, load50 = (json.loads((ROOT / 'artifacts' / 'hosting' / f'load-c{c}.json').read_text(encoding='utf-8')) for c in (10, 50))
chrome, firefox = (json.loads((ROOT / 'artifacts' / 'hosting' / 'performance' / f'homepage-{b}.json').read_text(encoding='utf-8')) for b in ('chromium', 'firefox'))

# Cover follows the institution/student/discipline layout of the supplied lab 2 report.
for line in [
    'МИНОБРНАУКИ РОССИИ',
    'федеральное государственное автономное образовательное учреждение',
    'высшего образования',
    '«Московский государственный технологический университет «СТАНКИН»',
    '(ФГАОУ ВО «МГТУ «СТАНКИН»)',
    'Институт информационных технологий',
    'Кафедра информационных технологий и вычислительных систем',
    '', 'ОТЧЕТ О ВЫПОЛНЕНИИ', 'ЛАБОРАТОРНОЙ РАБОТЫ № 4',
    'ПО ДИСЦИПЛИНЕ «Основы Web-технологий»', '',
    'СТУДЕНТА 3 КУРСА БАКАЛАВРИАТА ГРУППЫ ИДБ-24-17',
    'Ивкина Михаила Александровича', '',
    'НА ТЕМУ',
    '«Размещение на хостинге и тестирование веб-приложения',
    'музыкального фестиваля «Звук Фест»»', '',
    'Направление: 09.03.04 Программная инженерия',
    'Профиль: Разработка и сопровождение программного обеспечения', '',
    'Отчет сдан «______» ________________ 2026 г.',
    'Оценка ____________________________',
    'Преподаватель: Подвигина Е.А., доцент, кандидат педагогических наук',
    'Подпись ___________________________', '', 'МОСКВА 2026',
]:
    p = paragraph(line, centered=True)
    pp = p.find(f'{{{W}}}pPr')
    pp.append(el('spacing', {'line': 240, 'lineRule': 'auto', 'after': 60}))
    rp = el('rPr')
    rp.append(el('sz', {'val': 24}))
    p.find(f'{{{W}}}r').insert(0, rp)

heading('РЕФЕРАТ', new_page=True)
paragraph('ВЕБ-ПРИЛОЖЕНИЕ, ТЕСТИРОВАНИЕ, DJANGO, POSTGRESQL, PYTEST, PLAYWRIGHT, HTTP API, ХОСТИНГ, HTTPS, БЕЗОПАСНОСТЬ, ПРОИЗВОДИТЕЛЬНОСТЬ, НАГРУЗКА.')
paragraph('В работе выполнены размещение учебного сайта музыкального фестиваля «Звук Фест» на хостинге Netrun и разработка автоматизированных проверок его работоспособности. Сайт доступен по адресу https://zvukfest.de3.netrun.io. Проверены регистрация и авторизация пользователей, личный кабинет, каталог билетов, корзина, обращения и оформление учебных заказов. Проверки выполнялись через публичный HTTP API и в браузерах Chromium и Firefox.')
paragraph('Результаты зафиксированы в XML- и JSON-отчётах. Выявлены нарушения требований к защищённым cookie, раскрытие отладочной информации Django, превышение времени загрузки главной страницы и нестабильность отдельного сценария корзины в Firefox. При нагрузке по 100 запросов с параллельностью 10 и 50 все запросы завершились с HTTP 200, однако целевой порог p95 не выполнен. Полностью успешное прохождение всех проверок не подтверждено.')
paragraph('Отчёт подготовлен по сохранённым результатам по состоянию на 25 ноября 2026 года. Исторические локальные проверки и текущие проверки опубликованного сайта рассматриваются раздельно. Новый прогон в рамках подготовки отчёта не выполнялся.')

heading('СОДЕРЖАНИЕ', new_page=True)
for line in [
    'Введение', '1 Выбор направления исследования',
    '1.1 Анализ требований к тестированию', '1.2 Обоснование выбора инструментов',
    '2 Процесс размещения и тестирования веб-приложения',
    '2.1 Подготовка приложения и размещение на хостинге',
    '2.2 Организация тестовых сценариев и данных',
    '2.3 Функциональное тестирование API', '2.4 Тестирование интерфейса и адаптивности',
    '2.5 Проверка безопасности и параметров публикации',
    '2.6 Модульные проверки и тестирование базы данных',
    '2.7 Проверка скорости загрузки', '2.8 Нагрузочное тестирование',
    '2.9 Анализ неуспешных и невыполненных проверок',
    '3 Обобщение и оценка результатов', 'Заключение',
    'Приложение А. Материалы для иллюстрации результатов',
    'Приложение Б. Команды запуска и фрагмент теста',
    'Приложение В. Источники результатов',
]:
    paragraph(line, centered=False)
paragraph('Номера страниц содержания следует проставить после окончательной вёрстки и добавления скриншотов. Неподтверждённые номера страниц в отчёте не приводятся.')

heading('ВВЕДЕНИЕ', new_page=True)
paragraph('После публикации веб-приложения необходимо проверить не только корректность его программной логики, но и поведение в реальном окружении: доступность домена, TLS-сертификат, работу обратного прокси, раздачу статических ресурсов, сохранение сессий и время отклика. Успешный локальный запуск не гарантирует выполнения этих требований на хостинге.')
paragraph('Объект исследования — веб-приложение музыкального фестиваля «Звук Фест», включающее информационные страницы, каталог билетов, регистрацию, личный кабинет, корзину, обращения, учебные заказы и административный интерфейс. Предмет исследования — функциональная корректность, безопасность, совместимость с браузерами и производительность опубликованного приложения.')
paragraph('Цель работы — получить практические навыки развёртывания веб-приложения и организации воспроизводимого тестирования, выявить отклонения от требований и предложить меры их устранения.')
for line in [
    'Для достижения цели поставлены задачи:',
    '1. Разместить приложение на хостинге и проверить публичный адрес с HTTPS.',
    '2. Организовать автоматизированные проверки API и пользовательского интерфейса.',
    '3. Проверить валидацию, авторизацию, разделение данных пользователей и CSRF-защиту.',
    '4. Оценить адаптивность и работу приложения в двух браузерах.',
    '5. Измерить время загрузки и характеристики работы под нагрузкой.',
    '6. Сопоставить ожидаемые и фактические результаты, выделить ошибки и ограничения.',
]:
    paragraph(line)

heading('1 ВЫБОР НАПРАВЛЕНИЯ ИССЛЕДОВАНИЯ', new_page=True)
heading('1.1 Анализ требований к тестированию', 2)
paragraph('За основу приняты требования лабораторной работы «Хостинг, деплой и тестирование веб-приложения». Функциональные проверки охватывают открытие главной страницы по HTTPS, не менее десяти внутренних ссылок, загрузку изображений, CSS и JavaScript, отправку и валидацию форм. Интерфейс проверяется в Chromium и Firefox при ширинах 360, 768 и 1440 px. Целевое время полной загрузки главной страницы после пробуждения сервера — не более 3 секунд.')
paragraph('Для сравнения нагрузки используются два прогона по 100 запросов: с параллельностью 10 и 50. Измеряются среднее время, p95, число ошибок и пропускная способность. В используемом сценарии принят порог p95 ≤ 500 мс и отсутствие ошибок. Этот порог отражает выбранный критерий теста; он не является доказательством предельной мощности хостинга.')
paragraph('Критерии безопасности включают закрытость личных данных для гостей, изоляцию аккаунтов, CSRF-проверку, флаг Secure у cookie, отсутствие открытых конфигурационных файлов и публичных отладочных страниц. Статусы PASSED, FAILED, ERROR и SKIPPED учитываются раздельно.')
heading('1.2 Обоснование выбора инструментов', 2)
table(['Средство', 'Назначение'], [
    ['Python 3.13 / pytest 9.2.0', 'Написание сценариев, запуск проверок, формирование JUnit XML.'],
    ['Playwright 1.65.2 / pytest-playwright 0.10.0', 'Автоматизация действий в Chromium и Firefox.'],
    ['Django 6.1.3 / PostgreSQL 17', 'Серверная часть и база приложения; технические проверки в отдельной среде.'],
    ['Netrun / GitHub / Docker Compose', 'Публикация из репозитория, сервисы backend и db, переменные окружения.'],
    ['Navigation Timing / Resource Timing', 'Измерение загрузки страницы и ресурсов в браузере.'],
    ['ThreadPoolExecutor / HTTP-клиент Python', 'Ограниченная параллельная отправка GET-запросов для нагрузочного сравнения.'],
    ['XML и JSON', 'Проверяемые исходные данные отчёта и повторный анализ результатов.'],
], [3200, 6100])
paragraph('Версии приложения приведены по файлу зависимостей проекта; версии инструментов тестирования — по requirements-hosting.txt. Наличие версии в файле не заменяет отдельной инвентаризации всех компонентов фактически работающего контейнера.')

heading('2 ПРОЦЕСС РАЗМЕЩЕНИЯ И ТЕСТИРОВАНИЯ ВЕБ-ПРИЛОЖЕНИЯ', new_page=True)
heading('2.1 Подготовка приложения и размещение на хостинге', 2)
paragraph('Приложение опубликовано в Netrun из подключённого GitHub-репозитория. В конфигурации Compose предусмотрены сервис backend и PostgreSQL db с отдельным томом данных. Для домена zvukfest.de3.netrun.io настроены допустимые Host и Origin. Публичная точка входа использует HTTPS.')
paragraph('Конфиденциальные настройки вынесены в переменные окружения. Локальный .env исключён из Git; .env.example служит образцом без реальных секретных значений. Для создания администратора без интерактивной консоли добавлена команда bootstrap_admin, читающая DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_NAME и DJANGO_SUPERUSER_PASSWORD. Она не изменяет пароль существующего администратора и не повышает роль обычного пользователя с совпавшим email.')
paragraph('Размещение приложения подтверждается доступностью его публичных страниц и успешными запросами API. Наличие рабочего HTTPS не означает автоматически корректную настройку Secure-cookie или выключенный DEBUG; эти свойства проверяются отдельно.')
heading('2.2 Организация тестовых сценариев и данных', 2)
paragraph('Удалённые сценарии размещены в tests/hosting. Основной запуск выполняется скриптом scripts/run_site_tests.py. Набор api проверяет функции приложения через HTTP, ui — интерфейс в двух браузерах, checks — публикацию и безопасность. pytest.ini и pytest.ui.ini настроены на опубликованный сайт. Изолированные технические проверки сохранены в pytest.local.ini и pytest.ui.local.ini.')
paragraph('Для сценариев записи создаются уникальные аккаунты hosting-test-…@example.invalid. Их пароли генерируются на время выполнения и не сохраняются в файлах. Существующие билеты читаются из каталога без изменения цен и наличия. Тестовые обращения и учебные заказы остаются в базе и подлежат последующей ручной очистке через админку; чужие профили и корзины не используются.')
paragraph('Отчёты XML фиксируют результаты отдельных сценариев, JSON — параметры нагрузки и время загрузки ресурсов. Сбор тестов с --collect-only подтверждает только обнаружение сценариев и не считается успешным выполнением. Скрипт запуска не использует локальную рабочую базу при проверке опубликованного сайта.')
heading('2.3 Функциональное тестирование API', 2)
paragraph('Проверки выполнялись через реальные маршруты /api/register, /api/login, /api/profile, /api/password, /api/feedback, /api/search, /api/cart и /api/orders. Использовались положительные и отрицательные сценарии: корректные данные, нарушения правил ввода, повторные запросы, подмена идентификатора пользователя и отсутствие CSRF-токена.')
table(['Группа проверок', 'Содержание', 'Результат'], [
    ['Регистрация и вход', 'Обязательные поля и согласия, дубликат email, неверный пароль, повторный вход, смена аккаунта.', 'Пройдено.'],
    ['Профиль и пароль', 'Валидация, запрет повышения роли, смена пароля и прекращение другой сессии.', 'Пройдено.'],
    ['Обращения и поиск', 'Валидация обращений, закрытость чужих данных, ограничение истории поиска и просмотров.', 'Пройдено.'],
    ['Корзина', 'Допустимые количества, сохранение, очистка, изоляция, скидки и округление.', 'Пройдено.'],
    ['Заказы', 'Пустая корзина, неверный UUID, устаревшая сумма, повтор без дубликатов, история.', 'Пройдено в отдельных API-сценариях.'],
    ['Сквозной сценарий', 'Регистрация → корзина → заказ → выход → повторный вход → проверка cookie.', 'Действия выполнены; итог FAILED из-за отсутствия Secure.'],
], [1700, 4700, 2900])
paragraph('По api-results.xml выполнено 11 тестов: 10 PASSED и 1 FAILED. Проверка Secure расположена после повторного входа и выхода, поэтому неуспех сквозного теста относится к параметру безопасности cookie, а не означает, что оформление заказа не выполнялось.')
heading('2.4 Тестирование интерфейса и адаптивности', 2)
paragraph('Playwright воспроизводил действия пользователя: открытие страниц, ввод данных в формы, переход по ссылкам на правовые документы, вход, редактирование профиля, смену пароля, отправку обращения, просмотр билета, изменение количества, очистку корзины и оформление учебного заказа. Проверялось сохранение состояния после обновления страницы. Дополнительно контролировались ошибки JavaScript, загрузка ресурсов, смешанный HTTP/HTTPS-контент, подписи полей, клавиатурная навигация, слайдер и мобильное меню.')
paragraph('Адаптивность проверялась при ширинах 360, 768 и 1440 px на главной странице, странице билетов, корзине и политике конфиденциальности. Контролировалось отсутствие горизонтального переполнения; скриншоты сохранены в artifacts/hosting/layouts. Эти проверки подтверждают конкретные условия отображения, но не заменяют полный аудит доступности и оценку удобства реальными пользователями.')
paragraph('В ui-results.xml зарегистрировано 58 тестов: 53 PASSED, 3 FAILED и 2 SKIPPED. Два падения связаны со скоростью главной страницы; третье — со счётчиком корзины в Firefox. Вход в админку в обоих браузерах пропущен из-за отсутствия HOSTING_ADMIN_EMAIL и HOSTING_ADMIN_PASSWORD.')
heading('2.5 Проверка безопасности и параметров публикации', 2)
paragraph('Выполнены проверки DNS, доверенного TLS-сертификата и срока его действия, перенаправления HTTP на HTTPS, публичных страниц, внутренних ссылок, статики и оформления админки. API проверен на выдачу ожидаемых форматов данных и отказ гостям в доступе к профилю, корзине, заказам и журналам. Запросы без CSRF-токена и с посторонним Origin должны отклоняться.')
paragraph('По checks-results.xml выполнено 34 теста: 32 PASSED и 2 FAILED. Обнаружены отсутствие Secure у CSRF-cookie и отладочные сведения Django на странице ошибки. Аналогичная проблема session-cookie выявлена в функциональном наборе. Проверка защитных заголовков объединена с проверкой CSRF-cookie: при раннем падении дальнейшие утверждения этого конкретного теста не выполняются, поэтому результат не подтверждает их прохождение.')
paragraph('Проверки недоступности /.env, /.git/config, /compose.yaml, /db.sqlite3 и /zvukfest/settings.py прошли. Это подтверждает закрытость перечисленных HTTP-путей, но не является полным аудитом всех возможных утечек или всей инфраструктуры.')
heading('2.6 Модульные проверки и тестирование базы данных', 2)
paragraph('До размещения были выполнены изолированные серверные и браузерные проверки. В postgres-remaining-results.xml от 23.11.2026 сохранены 87 успешных XML-записей, соответствующих 84 тестам и 3 подтестам, без ошибок и пропусков. Проверялись миграции, внешние ключи, транзакции, параллельное оформление заказов и сохранение данных после перезапуска отдельного тестового PostgreSQL.')
paragraph('В локальном firefox-remaining-results.xml от 23.11.2026 зарегистрированы 30 успешных сценариев. В более раннем ui-results.xml от 20.11.2026, расположенном непосредственно в artifacts, сохранены 50 успешных проверок локального интерфейса. Эти отчёты относятся к прежним прогонам и не подтверждают автоматически состояние текущей публикации.')
paragraph('Проверки API через URL являются функциональными, а не unit-тестами отдельных Python-функций. Они не измеряют покрытие серверного кода. В ранее предоставленном снимке терминала зафиксировано покрытие 67,66% при требовании не менее 60%; это исторический результат конкретного запуска, а не актуальная оценка всех изменённых модулей. Для текущего отчёта о покрытии требуется отдельный запуск pytest-cov в тестовом окружении backend.')
paragraph('Прямую проверку схемы рабочей базы, применение всех миграций на хостинге, восстановление резервной копии и сохранность данных после повторного деплоя нельзя считать выполненными только на основании /api/health. Подтверждающие материалы этих операций в рассмотренных отчётах отсутствуют.')
heading('2.7 Проверка скорости загрузки', 2)
paragraph('Скорость измерялась через Navigation Timing: от начала навигации до завершения события load. Сервер предварительно пробуждался, но браузер использовал новый контекст с пустым кешем. В замер входят ресурсы страницы; ожидание пробуждения сервера фиксируется отдельно. Время готовности DOM и TTFB сохранены для диагностики и не подменяют полную загрузку.')
table(['Прогон', 'Chromium', 'Firefox', 'Критерий'], [
    ['Полный UI-набор, 25.11.2026', '4,663 с', '4,649 с', 'Оба значения выше 3 с.'],
    ['Диагностика, 25.11.2026 15:37 МСК', f'{chrome["load_ms"] / 1000:.3f} с', 'Событие load не наступило за 30 с ожидания', 'Оба теста FAILED.'],
    ['TTFB в диагностике', f'{chrome["ttfb_ms"]} мс', f'{firefox["ttfb_ms"]} мс', 'Диагностическая метрика, не полная загрузка.'],
], [3000, 1800, 2300, 2200])
paragraph('В Chromium загрузка dance-floor.jpg размером 2 969 948 байт заняла около 11,91 с, food-court.jpg размером 2 719 029 байт — около 11,75 с. В Firefox к моменту тайм-аута оставались незавершёнными запросы этих двух изображений и /api/cart. Измерения указывают на существенные задержки ресурсов, однако не позволяют отделить влияние сети, ограничений тарифа и обработки запросов сервером без дополнительных данных мониторинга.')
paragraph('Полная загрузка в двух прогонах различалась, поэтому результаты следует приводить с указанием условий и времени, а не выбирать только более быстрое значение. Предлагаемые меры: уменьшение размеров и веса изображений, настройка раздачи и кеширования статики, анализ очередей запросов и лимитов хостинга. Повышение порога теста не устраняет проблему производительности.')
heading('2.8 Нагрузочное тестирование', 2)
paragraph('Скрипт run_hosting_load.py выполняет 100 GET-запросов главной страницы за прогон. Перед измерением отправляется запрос для пробуждения. Параллельность ограничена 10 или 50 запросами; подготовка клиентов вынесена за пределы измерения. Каждый запрос получает HTML, без загрузки картинок и выполнения JavaScript. Длительность включает сеть, TLS и получение ответа.')
table(['Параллельность', 'Успех / ошибки', 'Среднее, мс', 'p95, мс', 'RPS', 'Итог'], [
    [str(d['concurrency']), f'{d["successes"]} / {d["errors"]}', f'{d["mean_ms"]:.2f}', f'{d["p95_ms"]:.2f}', f'{d["rps"]:.2f}', 'Порог p95 не выполнен']
    for d in (load10, load50)
], [1500, 1400, 1600, 1500, 1000, 2300])
paragraph('В таблице использованы последние сохранённые JSON-отчёты от 25.11.2026, а не более ранние значения из переписки. В обоих прогонах получено 100 ответов HTTP 200 без ошибок. При параллельности 10 значение p95 составило 1821,14 мс, при 50 — 2078,37 мс; оба значения превышают 500 мс. Таким образом, сайт выдержал короткие прогоны по доступности, но не выполнил выбранный критерий быстродействия.')
paragraph('Нельзя приравнивать 50 одновременных GET-запросов к 50 полноценным пользователям, выполняющим регистрацию и покупку. Прогоны не измеряют длительную устойчивость, предел масштабирования, CPU/RAM или производительность транзакций базы.')
heading('2.9 Анализ неуспешных и невыполненных проверок', 2)
table(['Проверка', 'Наблюдение и причина', 'Дальнейшее действие'], [
    ['test_registration_session_cart_order_and_relogin', 'FAILED: после сквозного сценария у session-cookie не найден Secure. Причина подтверждена проверкой атрибута.', 'Установить DJANGO_COOKIE_SECURE=true в окружении опубликованного backend, перезапустить и проверить заново.'],
    ['test_secure_csrf_cookie_and_headers', 'FAILED: у csrftoken отсутствует Secure; проверка заголовков в этом тесте остановлена ранним утверждением.', 'Включить Secure-cookie и повторить весь тест.'],
    ['test_missing_page_has_no_django_debug_details', 'FAILED: страница 404 содержит признаки отладочной страницы Django.', 'Отключить DEBUG в публикации, обеспечить статику и обычные страницы ошибок, затем перепроверить.'],
    ['test_homepage_load_budget — два браузера', 'FAILED: превышение 3 с; диагностически 12,978 с в Chromium и тайм-аут load в Firefox.', 'Оптимизировать ресурсы и их раздачу; измерить повторно при тех же условиях.'],
    ['test_ticket_details_cart_controls_and_demo_order[firefox]', 'FAILED: после повторного добавления билета #cart-badge оставался 0 вместо 1 в течение 5 с. Точная причина не установлена.', 'Сопоставить ответ PUT /api/cart, статус формы и обновление интерфейса. Возможна задержка, ошибка записи или обновления счётчика; нужны дополнительные данные.'],
    ['test_admin_login_with_hosting_credentials — два браузера', 'SKIPPED: не заданы HOSTING_ADMIN_EMAIL и HOSTING_ADMIN_PASSWORD.', 'Передать учётные данные через окружение процесса и выполнить проверку; не записывать пароль в репозиторий.'],
    ['Нагрузка c=10 и c=50', 'HTTP-ошибок нет, но p95 превышает 500 мс. JSON passed=false.', 'После оптимизации повторить оба режима и сравнить результаты с мониторингом.'],
], [2700, 3700, 2900])
paragraph('Полный запуск all-results.xml в 15:14 МСК завершился 102 ошибками подготовки из 103 проверок из-за общего ответа HTTP 503 при пробуждении Netrun; одна независимая проверка прошла. Эти 102 ошибки не означают 102 самостоятельных дефекта приложения. В код добавлено ограниченное ожидание готовности с повторами временных 502/503/504 до 60 секунд. После исправления механизма не зафиксирован единый полностью успешный запуск всего набора.')
paragraph('Ранний http-results.xml от 24.11.2026 отражает ограничение среды запуска: WinError 10013 и невозможность сетевого соединения. Эти ошибки не следует выдавать за недоступность сайта; для текущей оценки HTTP-проверок использован более поздний checks-results.xml.')
paragraph('Ранее также исправлены обработка отменённых при навигации запросов Firefox и преждевременное чтение пустого ключа сессии при смене аккаунта. Исправление кода само по себе не подтверждает успешность всех последующих сценариев. В последнем полном UI-отчёте остаётся отдельное падение счётчика корзины, описанное выше.')

heading('3 ОБОБЩЕНИЕ И ОЦЕНКА РЕЗУЛЬТАТОВ', new_page=True)
rows = []
for label, data in [('API, 25.11.2026', api), ('Публикация и безопасность, 25.11.2026', checks), ('UI в двух браузерах, 25.11.2026', ui)]:
    passed = data['tests'] - data['failures'] - data['errors'] - data['skipped']
    rows.append([label, data['tests'], passed, data['failures'], data['errors'], data['skipped']])
table(['Набор', 'Всего', 'PASSED', 'FAILED', 'ERROR', 'SKIPPED'], rows, [3500, 1100, 1200, 1200, 1100, 1200])
paragraph('По трём отдельным прогонам получено 95 успешных проверок, 6 падений и 2 пропуска из 103 сценариев. Это сводка отдельных запусков, а не результат одного успешного полного прогона. Два дополнительных диагностических теста производительности повторяют уже учитываемые проверки и не добавляются к сумме 103.')
paragraph('Основные функции приложения подтверждены выполненными сценариями: пользователи могут регистрироваться, входить, изменять профиль и пароль, пользоваться каталогом, корзиной, обращениями и учебными заказами. При этом выявленные настройки безопасности и нарушения быстродействия не позволяют признать выполнение всех требований полным.')
paragraph('Приоритет доработок: сначала устранить публичную отладку и включить Secure-cookie, затем исследовать сбой корзины Firefox и задержки ресурсов. После изменения настроек проверить админку и статику, после оптимизации повторить измерения загрузки и нагрузки. Завершающий этап — полный запуск всех наборов с сохранением нового отчёта и сравнением с исходными результатами.')
paragraph('Отчёты WAVE и Lighthouse с оценками доступности и производительности, актуальное покрытие изменённого backend, проверка восстановления резервной копии и подтверждение сохранности данных после деплоя не представлены. Эти пункты следует отметить как требующие отдельного выполнения; их нельзя заменить успешными HTTP-запросами.')

heading('ЗАКЛЮЧЕНИЕ', new_page=True)
paragraph('В ходе работы веб-приложение музыкального фестиваля «Звук Фест» размещено на хостинге Netrun и подготовлен набор автоматизированных проверок опубликованного сайта. Освоены функциональное тестирование API, автоматизация действий в браузере, проверка настроек публикации, сбор диагностических показателей загрузки и выполнение ограниченного нагрузочного сравнения.')
paragraph('Полученные результаты подтверждают работоспособность большинства проверенных пользовательских функций. Одновременно обнаружены отсутствие Secure у cookie, выдача отладочных сведений Django, превышение допустимого времени загрузки и непрохождение отдельного сценария корзины в Firefox. Две проверки административного входа не выполнены из-за отсутствия учётных данных. При нагрузке все запросы обработаны успешно по HTTP-статусу, но критерий p95 не достигнут.')
paragraph('Цель разработки тестов и анализа фактического поведения приложения достигнута. Полное выполнение требований к качеству опубликованного сайта пока не подтверждено. Для завершения работы необходимы устранение выявленных отклонений, выполнение пропущенных проверок и повторный полный прогон после внесённых изменений.')

heading('ПРИЛОЖЕНИЕ А', new_page=True)
heading('Материалы для иллюстрации результатов', 2)
paragraph('В итоговый вариант отчёта следует вставить перечисленные изображения с подписями. Существующие скриншоты адаптивности указаны как источники; скриншоты терминала и панели хостинга нужно добавить отдельно. Изображения, которых нет в материалах, не имитируются.')
table(['Подпись рисунка', 'Источник или что необходимо снять'], [
    ['Рисунок А.1 — Опубликованный сайт и HTTPS', 'Главная страница в браузере с адресной строкой https://zvukfest.de3.netrun.io.'],
    ['Рисунок А.2 — Сервисы приложения', 'Панель Netrun: работающие backend и db. Секретные значения не показывать.'],
    ['Рисунок А.3 — Мобильное отображение', 'artifacts/hosting/layouts/chromium/index-360.png.'],
    ['Рисунок А.4 — Планшетное отображение', 'artifacts/hosting/layouts/chromium/index-768.png.'],
    ['Рисунок А.5 — Отображение на компьютере', 'artifacts/hosting/layouts/chromium/index-1440.png.'],
    ['Рисунок А.6 — Итог API-проверок', 'Терминал запуска --suite api: 10 passed, 1 failed; сверить с api-results.xml.'],
    ['Рисунок А.7 — Итог интерфейсных проверок', 'Терминал --suite ui: 53 passed, 3 failed, 2 skipped; сверить с ui-results.xml.'],
    ['Рисунок А.8 — Диагностика загрузки', 'performance-results.xml и JSON с таблицей медленных ресурсов.'],
    ['Рисунок А.9 — Нагрузочное сравнение', 'load-c10.json и load-c50.json; подписи должны показывать passed=false.'],
    ['Рисунок А.10 — Дополнительные аудиты', 'WAVE и Lighthouse после фактического выполнения; до этого отметить отсутствие результата.'],
], [3700, 5600])

heading('ПРИЛОЖЕНИЕ Б', new_page=True)
heading('Команды запуска и фрагмент теста', 2)
paragraph('Команды выполняются из C:\\Users\\Дрыл\\Downloads\\Telegram Desktop\\zvukfest\\zvukfest после активации Python-окружения. Скрипт сам устанавливает корень репозитория рабочей папкой тестового процесса.')
for cmd in [
    'python ../scripts/run_site_tests.py',
    'python ../scripts/run_site_tests.py --suite api',
    'python ../scripts/run_site_tests.py --suite ui',
    'python ../scripts/run_site_tests.py --suite checks',
    'python ../scripts/run_site_tests.py --collect-only -q',
    'python ../scripts/run_site_tests.py --suite ui --no-writes -k homepage_load_budget',
    'python ../scripts/run_hosting_load.py --url https://zvukfest.de3.netrun.io --concurrency 10 --output ../artifacts/hosting/load-c10.json',
    'python ../scripts/run_hosting_load.py --url https://zvukfest.de3.netrun.io --concurrency 50 --output ../artifacts/hosting/load-c50.json',
]:
    paragraph(cmd, code=True)
paragraph('Пример действующей проверки доступа гостя к приватным данным (hosting_http.py):')
for line in [
    "@pytest.mark.parametrize('path', ['/api/profile', '/api/cart',",
    "    '/api/orders', '/api/actions', '/api/feedback'])",
    'def test_guest_cannot_read_private_data(site, path):',
    '    response = site.request(path)',
    '    assert response.status == 401',
    "    assert 'error' in response.json()",
]:
    paragraph(line, code=True)
paragraph('Пример демонстрирует проверку ожидаемого HTTP-статуса и структуры ответа через реальный сайт. Прямое подключение к базе или Django Test Client не используется.')

heading('ПРИЛОЖЕНИЕ В', new_page=True)
heading('Источники результатов', 2)
for source in [
    'Образец оформления: «Ивкин М.А._ ИДБ-24-17_отчет ЛР_2(1).docx».',
    'Требования: «Л.4 Хостинг, деплой и тестирование веб-приложения.docx».',
    'artifacts/hosting/api-results.xml — 25.11.2026, 15:15 МСК, 11 тестов.',
    'artifacts/hosting/checks-results.xml — 25.11.2026, 15:27 МСК, 34 теста.',
    'artifacts/hosting/ui-results.xml — 25.11.2026, 15:29 МСК, 58 тестов.',
    'artifacts/hosting/performance-results.xml — 25.11.2026, 15:37 МСК, повторная диагностика двух браузеров.',
    'artifacts/hosting/performance/homepage-chromium.json и homepage-firefox.json — подробные замеры ресурсов.',
    'artifacts/hosting/load-c10.json — 25.11.2026, 15:23 МСК; load-c50.json — 15:25 МСК.',
    'artifacts/hosting/all-results.xml — общий запуск с ошибкой пробуждения; не использовать как подтверждение функциональных дефектов всех 102 сценариев.',
    'artifacts/hosting/http-results.xml — ранний запуск с ограниченным сетевым доступом.',
    'artifacts/postgres-remaining-results.xml и artifacts/firefox-remaining-results.xml — исторические изолированные прогоны от 23.11.2026.',
    'artifacts/ui-results.xml — исторический локальный UI-прогон от 20.11.2026.',
    'TESTING.md, requirements-hosting.txt, tests/hosting и scripts/run_site_tests.py — организация проверок.',
]:
    paragraph(source)
paragraph('Показатели относятся к конкретным прогонам и условиям. После повторного запуска исходные файлы могут быть перезаписаны; для воспроизводимости перед сдачей следует сохранить их копию вместе с отчётом. Отсутствие приложенного результата не трактуется как успешное прохождение проверки.')

section = el('sectPr')
footer_ref = el('footerReference', {'type': 'default'})
footer_ref.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', 'rIdFooter')
section.append(footer_ref)
section.append(el('pgSz', {'w': 11906, 'h': 16838}))
section.append(el('pgMar', {'top': 1134, 'right': 850, 'bottom': 1134, 'left': 1701, 'header': 567, 'footer': 567, 'gutter': 0}))
section.append(el('titlePg'))
body.append(section)

styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="28"/><w:lang w:val="ru-RU"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="360" w:lineRule="auto"/><w:ind w:firstLine="709"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/><w:ind w:firstLine="0"/><w:jc w:val="center"/><w:spacing w:before="240" w:after="240"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/><w:ind w:firstLine="0"/><w:jc w:val="left"/><w:spacing w:before="200" w:after="160"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/></w:rPr></w:style></w:styles>'''
content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
package_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
document_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>'''
content_types = content_types.replace('</Types>', '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
footer = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="center"/><w:ind w:firstLine="0"/></w:pPr><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'''
OUT.mkdir(exist_ok=True)
stem = 'Отчет_ЛР4_тестирование_ЗвукФест'
with ZipFile(OUT / (stem + '.docx'), 'w', ZIP_DEFLATED) as archive:
    archive.writestr('[Content_Types].xml', content_types)
    archive.writestr('_rels/.rels', package_rels)
    archive.writestr('word/document.xml', ET.tostring(document, encoding='utf-8', xml_declaration=True))
    archive.writestr('word/styles.xml', styles)
    archive.writestr('word/_rels/document.xml.rels', document_rels)
    archive.writestr('word/footer1.xml', footer)
(OUT / (stem + '.txt')).write_text('\n\n'.join(plain), encoding='utf-8')
print('Created DOCX and TXT reports. Paragraphs:', len(list(body.iter(f'{{{W}}}p'))))
