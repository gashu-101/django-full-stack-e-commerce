(() => {
  'use strict';

  // ---------- Custom cursor (lerp follow) ----------
  const cursor = document.querySelector('.cursor');
  let mx = window.innerWidth / 2, my = window.innerHeight / 2;
  let cx = mx, cy = my;
  if (cursor) {
    window.addEventListener('mousemove', (e) => { mx = e.clientX; my = e.clientY; });
    const tick = () => {
      cx += (mx - cx) * 0.22;
      cy += (my - cy) * 0.22;
      cursor.style.transform = `translate(${cx}px, ${cy}px) translate(-50%,-50%)`;
      requestAnimationFrame(tick);
    };
    tick();
    document.querySelectorAll('[data-cursor="hover"], a, button, input, textarea').forEach(el => {
      el.addEventListener('mouseenter', () => cursor.classList.add('is-hover'));
      el.addEventListener('mouseleave', () => cursor.classList.remove('is-hover'));
    });
  }

  // ---------- Nav shadow on scroll ----------
  const nav = document.getElementById('nav');
  const onScroll = () => {
    if (window.scrollY > 8) nav?.classList.add('scrolled');
    else nav?.classList.remove('scrolled');
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // ---------- Reveal on scroll ----------
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));

  // Hero title — animate immediately on load
  requestAnimationFrame(() => {
    document.querySelector('.hero-title')?.classList.add('in');
  });

  // ---------- Quantity steppers ----------
  document.querySelectorAll('.qty').forEach(qty => {
    const input = qty.querySelector('input[type="number"]');
    qty.querySelectorAll('button[data-qty]').forEach(btn => {
      btn.addEventListener('click', () => {
        const step = parseInt(btn.dataset.qty, 10);
        const min = parseInt(input.min || '1', 10);
        const max = parseInt(input.max || '999', 10);
        const next = Math.max(min, Math.min(max, (parseInt(input.value, 10) || 1) + step));
        input.value = next;
      });
    });
  });

  // ---------- Cart pill bump on update ----------
  const pill = document.getElementById('cart-pill');
  let lastCount = pill ? parseInt(pill.textContent, 10) : 0;
  const observer = new MutationObserver(() => {
    const c = parseInt(pill.textContent, 10);
    if (c !== lastCount) {
      pill.classList.remove('bump');
      void pill.offsetWidth;
      pill.classList.add('bump');
      lastCount = c;
    }
  });
  if (pill) observer.observe(pill, { childList: true });

  // ---------- Smooth focus rings only for keyboard ----------
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') document.body.classList.add('using-keyboard');
  });
  document.addEventListener('mousedown', () => {
    document.body.classList.remove('using-keyboard');
  });
})();
