function showProductsMessage(message, retry = false) {
  const box = document.createElement('div');
  box.className = 'ticket-message';
  const text = document.createElement('p');
  text.textContent = message;
  box.append(text);
  if (retry) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button button_theme_dark';
    button.textContent = 'Повторить загрузку';
    button.addEventListener('click', () => loadProducts(searchForm.elements.query.value.trim()));
    box.append(button);
  }
  document.querySelector('#products-body').replaceChildren(box);
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

  const groups = new Map();
  for (const product of items) {
    const category = Array.isArray(product.categories) && product.categories.length
      ? product.categories[0]
      : {id: 'other', name: 'Другие билеты', alias: 'other'};
    const key = String(category.id ?? category.alias);
    if (!groups.has(key)) groups.set(key, {category, products: []});
    groups.get(key).products.push(product);
  }

  const sortedGroups = [...groups.values()].sort((left, right) => {
    const leftSchedule = `${left.category.performance_date || '9999'} ${left.category.performance_time || '99:99'}`;
    const rightSchedule = `${right.category.performance_date || '9999'} ${right.category.performance_time || '99:99'}`;
    return leftSchedule.localeCompare(rightSchedule) || left.category.name.localeCompare(right.category.name, 'ru');
  });

  for (const {category, products} of sortedGroups) {
    const categorySection = document.createElement('section');
    categorySection.className = 'ticket-category';
    const categoryHeader = document.createElement('header');
    categoryHeader.className = 'ticket-category__header';
    const categoryText = document.createElement('div');
    categoryText.className = 'ticket-category__text';
    const categoryTitle = document.createElement('h3');
    categoryTitle.className = 'ticket-category__title';
    categoryTitle.textContent = category.name;
    const details = [];
    if (category.performance_date) {
      const date = new Date(`${category.performance_date}T00:00:00`);
      details.push(date.toLocaleDateString('ru-RU', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'}));
    }
    if (category.performance_time) details.push(category.performance_time);
    const categoryDetails = document.createElement('p');
    categoryDetails.className = 'ticket-category__details';
    categoryDetails.textContent = details.join(' · ');
    categoryText.append(categoryTitle);
    if (details.length) categoryText.append(categoryDetails);
    categoryHeader.append(categoryText);
    const ticketGrid = document.createElement('div');
    ticketGrid.className = 'ticket-grid';
    categorySection.append(categoryHeader, ticketGrid);
    body.append(categorySection);

    for (const p of products) {
    const card = document.createElement('article');
    card.className = 'ticket-card ticket-product';
    const image = document.createElement('img');
    // Совместимость со старым кэшем api.js: отсутствие helper-а не должно
    // останавливать загрузку и отображение всего списка билетов.
    const imagePath = typeof ticketImage === 'function' ? ticketImage(p.image) : '';
    image.className = 'ticket-image'; image.src = imagePath;
    image.alt = ''; image.setAttribute('aria-hidden', 'true'); image.loading = 'lazy';
    if (imagePath) card.append(image);
    const cardBody = document.createElement('div');
    cardBody.className = 'ticket-card__body';
    const status = document.createElement('span');
    status.className = p.available ? 'ticket-card__status' : 'ticket-card__status ticket-card__status_sold';
    status.textContent = p.available ? 'В продаже' : 'Распродано';
    const title = document.createElement('h4');
    title.className = 'ticket-card__title'; title.textContent = p.name;
    const description = document.createElement('p');
    description.className = 'ticket-card__description'; description.textContent = p.short_description;
    const price = Number(p.unit_price) === 0 ? 'Бесплатно' : Number(p.unit_price).toLocaleString('ru-RU') + ' ₽' + (p.discount_percent ? ` (−${p.discount_percent}%)` : '');
    const footer = document.createElement('div');
    footer.className = 'ticket-card__footer';
    const priceText = document.createElement('strong');
    priceText.className = 'ticket-card__price'; priceText.textContent = price;
    const actions = document.createElement('div');
    actions.className = 'ticket-card__actions';
    const detailsButton = document.createElement('button');
    detailsButton.type = 'button'; detailsButton.className = 'ticket-details';
    detailsButton.textContent = 'Подробнее'; detailsButton.setAttribute('aria-label', `Подробнее: ${p.name}`);
    detailsButton.onclick = () => showTicket(p.id);
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'button button_theme_green';
    button.textContent = p.available ? 'В корзину' : 'Распродано'; button.disabled = !p.available;
    button.addEventListener('click', () => addToCart(p, button));
    actions.append(detailsButton, button);
    footer.append(priceText, actions);
    cardBody.append(status, title, description, footer);
    card.append(cardBody);
    ticketGrid.append(card);
    }
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
    const primaryImage = typeof ticketImage === 'function' ? ticketImage(p.image) : '';
    if (primaryImage) {
      const image = document.createElement('img');
      image.className = 'ticket-dialog__image'; image.src = primaryImage; image.alt = '';
      image.setAttribute('aria-hidden', 'true'); description.append(image);
    }
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
