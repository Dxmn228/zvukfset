(() => {
  const money = value => Number(value).toLocaleString('ru-RU', {style: 'currency', currency: 'RUB'});
  const trigger = document.createElement('button');
  trigger.type = 'button'; trigger.className = 'cart-fab'; trigger.id = 'cart-open';
  trigger.setAttribute('aria-label', 'Открыть корзину'); trigger.setAttribute('aria-haspopup', 'dialog');
  trigger.innerHTML = '<span aria-hidden="true">🛒</span><span id="cart-badge">0</span>';
  const dialog = document.createElement('dialog'); dialog.className = 'shop-dialog'; dialog.id = 'cart-dialog';
  dialog.setAttribute('aria-labelledby', 'mini-cart-title');
  dialog.innerHTML = '<button type="button" class="button button_theme_dark dialog-close" aria-label="Закрыть корзину">Закрыть</button><h2 id="mini-cart-title">Ваша корзина</h2><p role="status" id="mini-cart-status"></p><ul id="mini-cart-items" class="cart-items"></ul><p id="mini-cart-totals"></p><a class="button button_theme_green" href="cart.html">Перейти к оформлению</a>';
  document.body.append(trigger, dialog);
  const message = dialog.querySelector('[role="status"]');
  let busy = false;
  function render(cart) {
    document.querySelector('#cart-badge').textContent = cart ? cart.items.reduce((s, i) => s + i.quantity, 0) : 0;
    const list = dialog.querySelector('ul'); list.replaceChildren();
    dialog.querySelector('#mini-cart-totals').textContent = '';
    if (!cart) { message.textContent = 'Войдите в аккаунт, чтобы пользоваться корзиной.'; return; }
    message.textContent = cart.items.length ? '' : 'Корзина пока пуста.';
    for (const item of cart.items) {
      const row = document.createElement('li'); row.className = 'mini-cart-item';
      const image = document.createElement('img');
      const imagePath = typeof ticketImage === 'function' ? ticketImage(item.image) : '';
      image.className = 'mini-cart-item__image'; image.src = imagePath;
      image.alt = ''; image.setAttribute('aria-hidden', 'true'); image.loading = 'lazy';
      const text = document.createElement('p'); text.textContent = `${item.name} × ${item.quantity} — ${money(item.line_total)}`;
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'button button_theme_dark';
      remove.textContent = 'Удалить'; remove.setAttribute('aria-label', `Удалить из окна корзины: ${item.name}`);
      remove.onclick = async () => {
        if (busy) return; busy = true; remove.disabled = true;
        try {
          const result = await api('/api/cart', 'PUT', {items: cart.items.filter(i => i.product_id !== item.product_id).map(({product_id, quantity}) => ({product_id, quantity}))});
          if (!result.ok) message.textContent = result.body.error || 'Не удалось изменить корзину.';
        } catch { message.textContent = 'Нет связи с сервером. Повторите попытку.'; }
        finally { busy = false; remove.disabled = false; }
      };
      row.append(...(imagePath ? [image] : []), text, remove); list.append(row);
    }
    dialog.querySelector('#mini-cart-totals').textContent = `Без скидки: ${money(cart.subtotal)}. Скидка: ${money(cart.discount)}. Итого: ${money(cart.total)}.`;
  }
  async function refresh() {
    try {
      const result = await api('/api/cart');
      if (!result.ok && result.status !== 401) message.textContent = 'Не удалось загрузить корзину. Откройте её повторно.';
    } catch { message.textContent = 'Нет связи с сервером. Откройте корзину повторно.'; }
  }
  trigger.onclick = () => { dialog.showModal(); refresh(); };
  dialog.querySelector('.dialog-close').onclick = () => dialog.close();
  window.addEventListener('cart:updated', event => render(event.detail));
  window.addEventListener('storage', event => {
    if (CartCache.current && event.key === `zvukfest.cart.${CartCache.current.user_id}`) refresh();
  });
  // The cart page already fetches its own data.
  if (!document.querySelector('#cart-content')) refresh();
})();
