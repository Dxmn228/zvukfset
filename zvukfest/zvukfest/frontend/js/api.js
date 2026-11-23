// Достаёт значение cookie по имени (нужно для CSRF-токена)
function getCookie(name) {
  const row = document.cookie.split('; ').find((r) => r.startsWith(name + '='));
  return row ? decodeURIComponent(row.split('=')[1]) : '';
}

// Запрос к API: возвращает {ok, status, body}
let apiQueue = Promise.resolve();
function api(url, method = 'GET', data = null) {
  // Keep session-changing responses ordered (login, cart, viewed items, logout).
  const pending = apiQueue.then(() => sendApi(url, method, data));
  apiQueue = pending.catch(() => {});
  return pending;
}
async function sendApi(url, method, data) {
  const response = await fetch(url, {
    method,
    credentials: 'include',                        // передаём cookie с сессией
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
    body: data ? JSON.stringify(data) : null,
  });
  const body = await response.json().catch(() => ({}));
  if (response.ok && url === '/api/cart') CartCache.save(body);
  if (response.ok && url === '/api/orders' && method === 'POST') CartCache.save(body.cart);
  if (response.status === 401 || (response.ok && url === '/api/logout')) CartCache.clear();
  return { ok: response.ok, status: response.status, body };
}

// The database is authoritative. Cached selections are never submitted as prices.
const CartCache = {
  current: null,
  save(cart) {
    if (!cart || !Array.isArray(cart.items)) return;
    this.current = cart;
    try {
      for (const key of Object.keys(localStorage)) {
        if (key.startsWith('zvukfest.cart.') && key !== `zvukfest.cart.${cart.user_id}`) localStorage.removeItem(key);
      }
      localStorage.setItem(`zvukfest.cart.${cart.user_id}`, JSON.stringify(cart));
    } catch { /* The site also works when browser storage is disabled. */ }
    window.dispatchEvent(new CustomEvent('cart:updated', {detail: cart}));
  },
  clear() {
    this.current = null;
    try {
      for (const key of Object.keys(localStorage)) if (key.startsWith('zvukfest.cart.')) localStorage.removeItem(key);
    } catch { /* Storage is optional. */ }
    window.dispatchEvent(new CustomEvent('cart:updated', {detail: null}));
  }
};
