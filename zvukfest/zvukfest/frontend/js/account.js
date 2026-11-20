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
  if (!profile.ok) {                               // не авторизован: отправляем на вход
    location.href = 'tickets.html#login';
    return;
  }
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
}

document.querySelector('#logout').addEventListener('click', async () => {
  await api('/api/logout', 'POST');
  location.href = 'index.html';
});

loadAccount().catch(() => {
  document.querySelector('#account-info').textContent =
    'Не удалось загрузить данные личного кабинета. Проверьте соединение и обновите страницу.';
});
