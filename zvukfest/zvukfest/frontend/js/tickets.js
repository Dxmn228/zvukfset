function makeCell(text, tag = 'td') {
  const cell = document.createElement(tag);
  cell.className = 'table__cell';
  if (tag === 'th') cell.scope = 'row';
  cell.textContent = text;                         // textContent защищает от вставки html
  return cell;
}

function showProductsMessage(message, retry = false) {
  const row = document.createElement('tr');
  const cell = makeCell(message);
  cell.colSpan = 4;
  if (retry) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button button_theme_dark';
    button.textContent = 'Повторить загрузку';
    button.addEventListener('click', () => loadProducts(searchForm.elements.query.value.trim()));
    cell.append(document.createElement('br'), button);
  }
  row.append(cell);
  document.querySelector('#products-body').replaceChildren(row);
}

function renderProducts(items, isSearch = false) {
  const body = document.querySelector('#products-body');
  body.replaceChildren();
  if (!items.length) {
    showProductsMessage(isSearch
      ? 'По вашему запросу билеты не найдены. Измените запрос или очистите поиск.'
      : 'Билеты пока не добавлены. Загляните сюда позже.');
    return;
  }
  for (const p of items) {
    const row = document.createElement('tr');
    const price = Number(p.unit_price) === 0 ? 'Бесплатно' : Number(p.unit_price).toLocaleString('ru-RU') + ' ₽' + (p.discount_percent ? ` (−${p.discount_percent}%)` : '');
    const action = makeCell('');
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'button button_theme_green';
    button.textContent = p.available ? 'В корзину' : 'Распродано'; button.disabled = !p.available;
    button.addEventListener('click', () => addToCart(p, button)); action.append(button);
    row.append(makeCell(p.name, 'th'), makeCell(p.short_description), makeCell(price), action);
    const details = document.createElement('button'); details.type = 'button'; details.className = 'ticket-details';
    details.textContent = 'Подробнее'; details.setAttribute('aria-label', `Подробнее: ${p.name}`);
    details.onclick = () => showTicket(p.id); row.children[1].append(document.createElement('br'), details);
    body.append(row);
  }
}

const ticketDialog = document.createElement('dialog'); ticketDialog.className = 'shop-dialog'; ticketDialog.id = 'ticket-dialog';
ticketDialog.setAttribute('aria-labelledby', 'ticket-dialog-title');
ticketDialog.innerHTML = '<button type="button" class="button button_theme_dark dialog-close">Закрыть</button><h2 id="ticket-dialog-title">Описание билета</h2><div id="ticket-description" role="status"></div>';
document.body.append(ticketDialog);
ticketDialog.querySelector('button').onclick = () => ticketDialog.close();
async function showTicket(id) {
  ticketDialog.showModal();
  const description = ticketDialog.querySelector('#ticket-description'); description.textContent = 'Загружаем…';
  try {
    const result = await api(`/api/products/${id}`);
    if (!result.ok) throw new Error();
    const p = result.body; ticketDialog.querySelector('h2').textContent = p.name;
    description.replaceChildren();
    const text = document.createElement('p'); text.textContent = p.description || p.short_description; description.append(text);
    for (const prop of p.properties) {
      const line = document.createElement('p'); line.textContent = `${prop.property_name}: ${prop.property_value}`; description.append(line);
    }
    for (const picture of p.images) {
      const url = new URL(picture.image, location.href);
      if (url.origin !== location.origin || !url.pathname.startsWith('/img/')) continue;
      const img = document.createElement('img'); img.src = url.href; img.alt = picture.title || p.name; description.append(img);
    }
  } catch { description.textContent = 'Не удалось загрузить описание. Закройте окно и повторите попытку.'; }
}

// Форма поиска
const searchForm = document.querySelector('.search-form');
const searchStatus = searchForm.querySelector('.form__status');
let productsRequest = 0;

async function loadProducts(query = '') {
  const request = ++productsRequest;
  const body = document.querySelector('#products-body');
  body.setAttribute('aria-busy', 'true');
  searchStatus.textContent = 'Загружаем билеты…';
  showProductsMessage('Загружаем билеты…');
  try {
    const url = query ? '/api/search?q=' + encodeURIComponent(query) : '/api/products?sort=price';
    const result = await api(url);
    if (request !== productsRequest) return;
    if (!result.ok || !Array.isArray(result.body.items)) {
      throw new Error('Не удалось загрузить билеты. Повторите попытку.');
    }
    renderProducts(result.body.items, Boolean(query));
    searchStatus.textContent = query ? `Найдено билетов: ${result.body.items.length}.` : '';
  } catch {
    if (request !== productsRequest) return;
    const message = 'Не удалось загрузить билеты. Проверьте соединение и повторите попытку.';
    showProductsMessage(message, true);
    searchStatus.textContent = message;
  } finally {
    if (request === productsRequest) body.removeAttribute('aria-busy');
  }
}

searchForm.addEventListener('submit', (event) => {
  event.preventDefault();
  loadProducts(searchForm.elements.query.value.trim());
});
loadProducts();
let adding = false;
async function addToCart(product, button) {
  if (adding) return; adding = true; button.disabled = true; button.classList.add('button_loading');
  searchStatus.textContent = '';
  try {
    const current = await api('/api/cart');
    if (current.status === 401) { searchStatus.textContent = 'Войдите, чтобы добавить билеты в корзину.'; location.hash = 'login'; return; }
    if (!current.ok) throw new Error('Не удалось загрузить корзину.');
    const items = current.body.items.map(({product_id,quantity}) => ({product_id,quantity}));
    const existing = items.find(i => i.product_id === product.id);
    if (existing && existing.quantity >= 20) throw new Error('В корзине уже 20 билетов этого типа.');
    if (existing) existing.quantity++; else items.push({product_id:product.id,quantity:1});
    const result = await api('/api/cart','PUT',{items});
    if (!result.ok) throw new Error(result.body.error || 'Не удалось добавить билет.');
    if (!result.body.items.some(i => i.product_id === product.id)) throw new Error('Билет больше недоступен.');
    const link = document.createElement('a'); link.href = 'cart.html'; link.textContent = 'Перейти в корзину';
    searchStatus.replaceChildren(document.createTextNode('Билет добавлен. '),link);
  } catch (error) { searchStatus.textContent = error instanceof TypeError ? 'Нет связи с сервером. Повторите попытку.' : error.message; }
  finally { adding = false; button.disabled = false; button.classList.remove('button_loading'); }
}
