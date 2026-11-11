// 1. Бургер-меню
const burger = document.querySelector('.burger');
const navList = document.querySelector('.nav__list');

function setMenu(isOpen) {
  navList.classList.toggle('active', isOpen);
  burger.setAttribute('aria-expanded', isOpen);
  burger.setAttribute('aria-label', isOpen ? 'Закрыть меню' : 'Открыть меню');
}

burger.addEventListener('click', () => {
  setMenu(burger.getAttribute('aria-expanded') !== 'true');
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') setMenu(false);
});

// 2. Проверка совпадения паролей (только на странице с регистрацией)
const registerForm = document.querySelector('.form_type_register');

if (registerForm) {
  const password = registerForm.elements['password'];
  const confirm = registerForm.elements['password_confirm'];

  function checkPasswords() {
    confirm.setCustomValidity(password.value === confirm.value ? '' : 'Пароли не совпадают');
  }
  password.addEventListener('input', checkPasswords);
  confirm.addEventListener('input', checkPasswords);
}

// 3. Отправка форм на сервер (формы с атрибутом data-api)
function formToObject(form) {
  const data = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    data[el.name] = el.type === 'checkbox' ? el.checked : el.value;
  }
  return data;
}

document.querySelectorAll('.form[data-api]').forEach((form) => {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();                       // не даём браузеру отправить форму самому
    const button = form.querySelector('button[type="submit"]');
    const status = form.querySelector('.form__status');
    button.classList.add('button_loading');
    button.disabled = true;
    status.textContent = '';

    const result = await api(form.dataset.api, form.dataset.method || 'POST', formToObject(form));

    button.classList.remove('button_loading');
    button.disabled = false;

    if (!result.ok) {                             // сервер вернул ошибки
      const errors = result.body.errors
        ? Object.values(result.body.errors)
        : [result.body.error || `Ошибка сервера (код ${result.status})`];
      status.textContent = errors.join(' ');
      return;
    }
    if (form.dataset.redirect) {
      location.href = form.dataset.redirect;
      return;
    }
    if ('reset' in form.dataset) form.reset();
    status.textContent = result.body.message || 'Готово!';
  });
});