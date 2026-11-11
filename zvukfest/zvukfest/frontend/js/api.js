// Достаёт значение cookie по имени (нужно для CSRF-токена)
function getCookie(name) {
  const row = document.cookie.split('; ').find((r) => r.startsWith(name + '='));
  return row ? decodeURIComponent(row.split('=')[1]) : '';
}

// Запрос к API: возвращает {ok, status, body}
async function api(url, method = 'GET', data = null) {
  const response = await fetch(url, {
    method,
    credentials: 'include',                        // передаём cookie с сессией
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
    body: data ? JSON.stringify(data) : null,
  });
  const body = await response.json().catch(() => ({}));
  return { ok: response.ok, status: response.status, body };
}