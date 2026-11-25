const status = document.querySelector('#cart-status');
const content = document.querySelector('#cart-content');
const list = document.querySelector('#cart-items');
const money = value => new Intl.NumberFormat('ru-RU', {style:'currency',currency:'RUB'}).format(value);
let items = [];
let busy = false;
let quote = '';
let requestId = null;
function render() {
  content.hidden = !items.length;
  document.querySelector('#cart-empty').hidden = !!items.length;
  list.replaceChildren();
  for (const item of items) {
    const row = document.createElement('li'); row.className = 'cart-item';
    const image = document.createElement('img');
    const imagePath = typeof ticketImage === 'function' ? ticketImage(item.image) : '';
    image.className = 'cart-item__image'; image.src = imagePath;
    image.alt = ''; image.setAttribute('aria-hidden', 'true'); image.loading = 'lazy';
    const title = document.createElement('h3'); title.textContent = item.name;
    const price = document.createElement('p'); price.textContent = money(item.unit_price) + ' за билет' + (item.discount_percent ? ` (скидка ${item.discount_percent}%)` : '') + (!item.available ? ' — больше недоступен' : '');
    const controls = document.createElement('div'); controls.className = 'cart-controls';
    const count = document.createElement('span'); count.textContent = item.quantity;
    function button(text, label, action, disabled = false) {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'button button_theme_dark';
      b.textContent = text; b.setAttribute('aria-label', label + ': ' + item.name); b.disabled = disabled;
      b.addEventListener('click', action); return b;
    }
    const change = delta => save(items.map(i => i.product_id === item.product_id ? {...i, quantity:i.quantity + delta} : i));
    controls.append(button('−','Уменьшить количество',() => change(-1),item.quantity <= 1),count,
      button('+','Увеличить количество',() => change(1),item.quantity >= 20),
      button('Удалить','Удалить',() => save(items.filter(i => i.product_id !== item.product_id))));
    const subtotal = document.createElement('strong'); subtotal.textContent = money(item.line_total);
    row.append(...(imagePath ? [image] : []), title,price,controls,subtotal); list.append(row);
  }
  document.querySelector('#cart-total').textContent = money(CartCache.current?.total || 0);
  document.querySelector('#cart-subtotal').textContent = money(CartCache.current?.subtotal || 0);
  document.querySelector('#cart-discount').textContent = money(CartCache.current?.discount || 0);
  document.querySelector('#cart-count').textContent = items.reduce((s,i) => s + i.quantity,0);
}
function login() {
  content.hidden = true; document.querySelector('#cart-empty').hidden = true;
  document.querySelector('#cart-login').hidden = false; status.textContent = '';
}
async function save(next) {
  if (busy) return; busy = true;
  const buttons = [...content.querySelectorAll('button')]; const previous = buttons.map(b => b.disabled);
  buttons.forEach(b => b.disabled = true); content.setAttribute('aria-busy','true'); status.textContent = 'Сохраняем…';
  try {
    const result = await api('/api/cart','PUT',{items:next.map(({product_id,quantity}) => ({product_id,quantity}))});
    if (result.status === 401) { login(); return; }
    if (!result.ok) throw new Error(result.body.error || 'Не удалось сохранить корзину.');
    requestId = null;
    items = result.body.items; render(); status.textContent = 'Корзина сохранена.';
  } catch (error) {
    status.textContent = error instanceof TypeError ? 'Нет связи с сервером. Повторите попытку.' : error.message;
  } finally {
    buttons.forEach((b,i) => b.disabled = previous[i]);
    busy = false;
    content.removeAttribute('aria-busy');
  }
}
document.querySelector('#cart-clear').addEventListener('click',() => save([]));
window.addEventListener('cart:updated', event => {
  if (!event.detail) { login(); return; }
  items = event.detail.items; quote = event.detail.quote; render();
});
document.querySelector('#cart-checkout').addEventListener('click', async () => {
  if (busy) return;
  busy = true;
  const buttons = [...content.querySelectorAll('button')];
  const previous = buttons.map(b => b.disabled); buttons.forEach(b => b.disabled = true);
  requestId ||= crypto.randomUUID();
  status.textContent = 'Создаём заказ…';
  try {
    const result = await api('/api/orders', 'POST', {quote, request_id: requestId});
    if (!result.ok) {
      if (result.status === 401) login();
      if (result.status === 409) { requestId = null; await api('/api/cart'); }
      throw new Error(result.body.error || 'Не удалось оформить заказ. Повторите попытку.');
    }
    requestId = null;
    status.replaceChildren(document.createTextNode(`Учебный заказ №${result.body.order.id} создан. Оплата не производится. `));
    const link = document.createElement('a'); link.href = 'account.html#orders'; link.textContent = 'История заказов'; status.append(link);
  } catch (error) { status.textContent = error instanceof TypeError ? 'Нет связи с сервером. Повторите оформление.' : error.message; }
  finally { busy = false; buttons.forEach((b, i) => b.disabled = previous[i]); }
});
(async () => {
  try {
    const result = await api('/api/cart');
    if (result.status === 401) { login(); return; }
    if (!result.ok) throw new Error();
    items = result.body.items; render(); status.textContent = '';
  } catch { status.textContent = 'Не удалось загрузить корзину. Проверьте соединение и обновите страницу.'; }
})();
