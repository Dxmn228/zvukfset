function fillList(selector, lines) {
  const list = document.querySelector(selector);
  list.replaceChildren();
  for (const text of lines.length ? lines : ['Пока пусто']) {
    const item = document.createElement('li');
    item.textContent = text;
    list.append(item);
  }
}

async function loadAccount() {
  const profile = await api('/api/profile');
  if (profile.status === 401) {                    // не авторизован: отправляем на вход
    location.href = 'tickets.html#login';
    return;
  }
  if (!profile.ok) throw new Error('Не удалось загрузить профиль');
  const form = document.querySelector('#profile-form');
  form.elements['name'].value = profile.body.name;
  form.elements['email'].value = profile.body.email;
  form.elements['phone'].value = profile.body.phone;
  const role = profile.body.role === 'admin' ? 'администратор' : 'пользователь';
  document.querySelector('#account-info').textContent =
    `Роль: ${role}. Регистрация: ${profile.body.created_at}. Последний вход: ${profile.body.last_login}.`;

  const feedback = await api('/api/feedback');
  fillList('#feedback-list', feedback.body.items.map(
    (f) => `${f.created_at}: ${f.subject}. ${f.message} (${f.status})`));

  const actions = await api('/api/actions');
  fillList('#actions-list', actions.body.items.map((a) => `${a.created_at}: ${a.action} ${a.page}`));
  fillList('#viewed-list', actions.body.last_viewed.map((p) => p.name));
  fillList('#search-list', actions.body.search_history);
  const orders = await api('/api/orders');
  if (!orders.ok) throw new Error('Не удалось загрузить заказы');
  const list = document.querySelector('#orders-list'); list.replaceChildren();
  if (!orders.body.items.length) fillList('#orders-list', []);
  for (const order of orders.body.items) {
    const row = document.createElement('li'); row.className = 'cart-item';
    const title = document.createElement('h3'); title.textContent = `Заказ №${order.id} от ${order.created_at}`;
    const state = document.createElement('p'); state.textContent = order.status;
    const products = document.createElement('ul');
    for (const item of order.items) {
      const line = document.createElement('li'); line.textContent = `${item.name} × ${item.quantity} — ${item.unit_price} ₽ за билет`; products.append(line);
    }
    const total = document.createElement('p'); total.textContent = `Без скидки: ${order.subtotal} ₽. Скидка: ${order.discount} ₽. Итого: ${order.total} ₽.`;
    row.append(title, state, products, total); list.append(row);
  }
}

document.querySelector('#logout').addEventListener('click', async () => {
  await api('/api/logout', 'POST');
  location.href = 'index.html';
});

loadAccount().catch(() => {
  document.querySelector('#account-info').textContent =
    'Не удалось загрузить данные личного кабинета. Проверьте соединение и обновите страницу.';
});
