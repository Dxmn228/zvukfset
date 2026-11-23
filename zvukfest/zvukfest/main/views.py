import json
import logging
import hashlib
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from html.parser import HTMLParser
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import connection, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .forms import FeedbackForm, LoginForm, PasswordForm, ProfileForm, RegisterForm
from .models import CartItem, Feedback, Product, User, UserSession, Order, OrderItem

logger = logging.getLogger(__name__)


# ---------- вспомогательные функции ----------
def get_json(request):
    """Читает JSON из тела запроса (если там мусор, вернёт пустой словарь)."""
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def form_errors(form):
    """{'поле': 'первая ошибка'}; ошибки не относящиеся к полю лежат в '__all__'."""
    return {field: errors[0] for field, errors in form.errors.items()}


def fmt(dt):
    return timezone.localtime(dt).strftime('%d.%m.%Y %H:%M') if dt else None


def user_data(user):
    return {'name': user.name, 'email': user.email, 'phone': user.phone, 'role': user.role,
            'created_at': fmt(user.created_at), 'last_login': fmt(user.last_login)}


def product_data(p):
    return {'id': p.id, 'name': p.name, 'alias': p.alias, 'short_description': p.short_description,
            'price': float(p.price), 'unit_price': str(discounted_price(p)),
            'discount_percent': p.discount_percent, 'image': p.image, 'available': p.available}


def log_action(request, action, page=None):
    """Запись в журнал user_actions (только для вошедших пользователей)."""
    if request.user.is_authenticated:
        request.user.actions.create(action=action, page=(page or request.path)[:255])


def api_login_required(view):
    """Аналог middleware requireAuth: без входа отвечаем 401."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Не авторизован'}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def start_session(request, user, remember=True):
    login(request, user)                     # создаёт сессию и обновляет last_login
    if not remember:
        request.session.set_expiry(0)        # сессия живёт до закрытия браузера
    UserSession.objects.create(
        user=user,
        session_token=request.session.session_key,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        expires_at=request.session.get_expiry_date(),
    )
    cart_payload(request)


# ---------- страницы фронтенда ----------
@ensure_csrf_cookie                           # выдаёт браузеру cookie csrftoken
def page(request, name='index'):
    if name == 'account' and not request.user.is_authenticated:
        return HttpResponseRedirect('/tickets.html#login')
    file = settings.FRONTEND_DIR / f'{name}.html'
    if not file.is_file():
        raise Http404
    return HttpResponse(file.read_text(encoding='utf-8'))


class PolicyText(HTMLParser):
    """Download the same document shown in the browser, without site navigation."""
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'main':
            self.inside = True
        if self.inside and tag in ('p', 'h1', 'h2', 'li'):
            self.parts.append('\n\n')

    def handle_endtag(self, tag):
        if tag == 'main':
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.parts.append(data.strip() + ' ' if data.strip() else '')


@require_http_methods(['GET'])
def privacy_download(request):
    parser = PolicyText()
    parser.feed((settings.FRONTEND_DIR / 'privacy.html').read_text(encoding='utf-8'))
    response = HttpResponse(''.join(parser.parts).strip(), content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="privacy-policy.txt"'
    return response


# ---------- проверка подключения к БД ----------
def health(request):
    try:
        connection.ensure_connection()
    except Exception:
        logger.exception('Не удалось подключиться к БД')
        return JsonResponse({'status': 'error', 'message': 'База данных недоступна'}, status=503)
    return JsonResponse({'status': 'ok'})


# ---------- регистрация / вход / выход ----------
@require_http_methods(['POST'])
def register(request):
    form = RegisterForm(get_json(request))
    if not form.is_valid():
        return JsonResponse({'errors': form_errors(form)}, status=400)
    d = form.cleaned_data
    user = User.objects.create_user(email=d['email'], name=d['username'],
                                    password=d['password'], phone=d['phone'])
    start_session(request, user)
    log_action(request, 'register')
    return JsonResponse({'message': 'Регистрация прошла успешно'}, status=201)


@require_http_methods(['POST'])
def login_view(request):
    form = LoginForm(get_json(request))
    if not form.is_valid():
        return JsonResponse({'errors': form_errors(form)}, status=400)
    d = form.cleaned_data
    user = authenticate(request, username=d['email'].lower(), password=d['password'])
    if user is None:
        return JsonResponse({'errors': {'__all__': 'Неверный email или пароль'}}, status=401)
    start_session(request, user, d['remember'])
    log_action(request, 'login')
    return JsonResponse({'message': 'Вы вошли в систему', 'role': user.role})


@require_http_methods(['POST'])
@api_login_required
def logout_view(request):
    log_action(request, 'logout')
    logout(request)
    return JsonResponse({'message': 'Вы вышли из системы'})


# ---------- профиль ----------
@require_http_methods(['GET', 'PUT'])
@api_login_required
def profile(request):
    user = request.user
    message = None
    if request.method == 'PUT':
        form = ProfileForm(get_json(request), user=user)
        if not form.is_valid():
            return JsonResponse({'errors': form_errors(form)}, status=400)
        d = form.cleaned_data
        user.name, user.email, user.phone = d['name'], d['email'], d['phone']
        user.save()
        log_action(request, 'update_profile')
        message = 'Профиль сохранён'
    return JsonResponse({**user_data(user), 'message': message})


@require_http_methods(['POST'])
@api_login_required
def change_password(request):
    form = PasswordForm(get_json(request), user=request.user)
    if not form.is_valid():
        return JsonResponse({'errors': form_errors(form)}, status=400)
    request.user.set_password(form.cleaned_data['new_password'])
    request.user.save()
    update_session_auth_hash(request, request.user)   # чтобы пользователя не выбросило из сессии
    log_action(request, 'change_password')
    return JsonResponse({'message': 'Пароль изменён'})


# ---------- обратная связь ----------
@require_http_methods(['GET', 'POST'])
def feedback(request):
    if request.method == 'GET':               # свои обращения для личного кабинета
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Не авторизован'}, status=401)
        items = [{'id': f.id, 'subject': f.get_subject_display(), 'message': f.message,
                  'rating': f.rating, 'status': f.get_status_display(),
                  'created_at': fmt(f.created_at)} for f in request.user.feedbacks.all()]
        return JsonResponse({'items': items})

    form = FeedbackForm(get_json(request))
    if not form.is_valid():
        return JsonResponse({'errors': form_errors(form)}, status=400)
    d = form.cleaned_data
    Feedback.objects.create(
        user=request.user if request.user.is_authenticated else None,
        name=d['name'], email=d['email'], phone=d['phone'],
        subject=d['subject'], message=d['message'], rating=d['rating'])
    log_action(request, 'send_feedback')
    return JsonResponse({'message': 'Спасибо! Сообщение отправлено.'}, status=201)


# ---------- товары и поиск ----------
@require_http_methods(['GET'])
def products(request):
    items = Product.objects.all()
    if request.GET.get('category'):
        items = items.filter(categories__alias=request.GET['category'])
    sorting = {'price': 'price', '-price': '-price', 'name': 'name'}
    items = items.order_by(sorting.get(request.GET.get('sort'), 'id'))
    return JsonResponse({'items': [product_data(p) for p in items]})


@require_http_methods(['GET'])
def product_detail(request, pk):
    try:
        p = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)
    data = product_data(p)
    data['description'] = p.description
    data['properties'] = list(p.properties.values('property_name', 'property_value', 'property_price'))
    data['images'] = list(p.images.values('image', 'title'))
    # Последние 5 просмотренных товаров храним в сессии
    viewed = [v for v in request.session.get('last_viewed', []) if v['id'] != p.id]
    request.session['last_viewed'] = ([{'id': p.id, 'name': p.name}] + viewed)[:5]
    log_action(request, 'view_product', f'/api/products/{p.id}')
    return JsonResponse(data)


@require_http_methods(['GET'])
def search(request):
    q = request.GET.get('q', '').strip()
    if not 2 <= len(q) <= 100:
        return JsonResponse({'errors': {'q': 'Введите от 2 до 100 символов'}}, status=400)
    found = Product.objects.filter(
        Q(name__icontains=q) | Q(short_description__icontains=q) | Q(description__icontains=q))[:20]
    # История поиска (5 последних запросов) лежит в сессии
    history = [h for h in request.session.get('search_history', []) if h != q]
    request.session['search_history'] = ([q] + history)[:5]
    log_action(request, 'search', f'q={q}')
    return JsonResponse({'query': q, 'items': [product_data(p) for p in found]})


# ---------- журнал действий ----------
@require_http_methods(['GET'])
@api_login_required
def actions(request):
    items = [{'action': a.action, 'page': a.page, 'created_at': fmt(a.created_at)}
             for a in request.user.actions.all()[:10]]
    return JsonResponse({'items': items,
                         'last_viewed': request.session.get('last_viewed', []),
                         'search_history': request.session.get('search_history', [])})


# ---------- корзина (привязка к пользователю в БД) ----------
def discounted_price(product):
    return (product.price * (100 - product.discount_percent) / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def cart_payload(request):
    items = []
    subtotal = total = Decimal('0.00')
    for row in request.user.cart_items.select_related('product').order_by('product_id'):
        p = row.product
        unit_price = discounted_price(p)
        subtotal += p.price * row.quantity
        total += unit_price * row.quantity
        items.append({'product_id': p.id, 'name': p.name, 'price': str(p.price),
                      'unit_price': str(unit_price), 'discount_percent': p.discount_percent,
                      'quantity': row.quantity, 'available': p.available,
                      'line_total': str(unit_price * row.quantity)})
    selection = [{'product_id': i['product_id'], 'quantity': i['quantity']} for i in items]
    if request.session.get('cart') != selection:
        request.session['cart'] = selection
    quote = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
    return {'user_id': request.user.pk, 'items': items, 'subtotal': str(subtotal),
            'discount': str(subtotal - total), 'total': str(total), 'quote': quote}


@require_http_methods(['GET', 'PUT'])
@api_login_required
def cart(request):
    if request.method == 'PUT':               # PUT полностью заменяет корзину пользователя
        items = get_json(request).get('items')
        if not isinstance(items, list):
            return JsonResponse({'error': 'Неверный формат корзины'}, status=400)
        quantities = {}
        try:
            for item in items:
                if not isinstance(item, dict) or type(item.get('product_id')) is not int or type(item.get('quantity')) is not int:
                    raise ValueError()
                if item['product_id'] in quantities:
                    raise ValueError()
                quantities[item['product_id']] = item['quantity']
        except (KeyError, TypeError, ValueError):
            return JsonResponse({'error': 'Неверный формат корзины'}, status=400)
        if any(q < 1 or q > 20 for q in quantities.values()):
            return JsonResponse({'error': 'Количество должно быть от 1 до 20'}, status=400)
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            found = list(Product.objects.select_for_update().filter(id__in=quantities, available=True))
            if len(found) != len(quantities):
                return JsonResponse({'error': 'Один из билетов больше недоступен. Обновите корзину.'}, status=409)
            request.user.cart_items.all().delete()
            CartItem.objects.bulk_create(
                [CartItem(user=request.user, product=p, quantity=quantities[p.id]) for p in found])
        log_action(request, 'update_cart')
    return JsonResponse(cart_payload(request))


def order_data(order):
    return {'id': order.pk, 'created_at': fmt(order.created_at), 'status': order.get_status_display(),
            'subtotal': str(order.subtotal), 'discount': str(order.discount), 'total': str(order.total),
            'items': [{'name': i.name, 'quantity': i.quantity, 'unit_price': str(i.unit_price)} for i in order.items.all()]}


@require_http_methods(['GET', 'POST'])
@api_login_required
def orders(request):
    if request.method == 'GET':
        return JsonResponse({'items': [order_data(o) for o in request.user.orders.prefetch_related('items')]})
    data = get_json(request)
    try:
        request_id = UUID(str(data.get('request_id', '')))
    except ValueError:
        return JsonResponse({'error': 'Неверный идентификатор заказа'}, status=400)
    with transaction.atomic():
        User.objects.select_for_update().get(pk=request.user.pk)
        previous = request.user.orders.filter(request_id=request_id).first()
        if previous:
            return JsonResponse({'order': order_data(previous), 'cart': cart_payload(request)})
        product_ids = list(request.user.cart_items.values_list('product_id', flat=True))
        list(Product.objects.select_for_update().filter(pk__in=product_ids).order_by('pk'))
        current = cart_payload(request)
        if not current['items']:
            return JsonResponse({'error': 'Корзина пуста'}, status=400)
        if any(not i['available'] or Decimal(i['price']) < 0 for i in current['items']):
            return JsonResponse({'error': 'В корзине есть недоступный билет. Удалите его перед оформлением.'}, status=409)
        if data.get('quote') != current['quote']:
            return JsonResponse({'error': 'Состав или цена корзины изменились. Обновите корзину и проверьте сумму.'}, status=409)
        order = Order.objects.create(user=request.user, request_id=request_id,
                                     subtotal=current['subtotal'], discount=current['discount'], total=current['total'])
        OrderItem.objects.bulk_create([OrderItem(order=order, product_id=i['product_id'], name=i['name'],
                                                price=i['price'], unit_price=i['unit_price'], quantity=i['quantity'])
                                       for i in current['items']])
        request.user.cart_items.all().delete()
        log_action(request, 'place_order', f'order/{order.pk}')
        return JsonResponse({'order': order_data(order), 'cart': cart_payload(request)}, status=201)
