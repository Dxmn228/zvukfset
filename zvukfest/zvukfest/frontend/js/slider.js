(() => {
  const root = document.querySelector('.festival-slider');
  if (!root) return;
  const slides = [...root.querySelectorAll('.festival-slide')];
  let current = 0;
  function show(index) {
    current = (index + slides.length) % slides.length;
    slides.forEach((slide, i) => slide.hidden = i !== current);
    root.querySelector('[role="status"]').textContent = `Слайд ${current + 1} из ${slides.length}`;
  }
  root.querySelector('[data-prev]').onclick = () => show(current - 1);
  root.querySelector('[data-next]').onclick = () => show(current + 1);
  root.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault(); show(current + (event.key === 'ArrowRight' ? 1 : -1));
    }
  });
  show(0);
})();
