// Sevara Design — sayt interfeysi uchun kichik vanilla JS

(function () {
  'use strict';

  // --- Mobil menyu -------------------------------------------------------
  const menuToggle = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('[data-menu]');
  if (menuToggle && menu) {
    menuToggle.addEventListener('click', function () {
      menu.classList.toggle('open');
    });
  }

  // --- Modal (qo'ng'iroq so'rash) ----------------------------------------
  document.querySelectorAll('[data-modal-open]').forEach(function (button) {
    button.addEventListener('click', function () {
      const modal = document.getElementById('modal-' + button.dataset.modalOpen);
      if (modal) {
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
      }
    });
  });

  function closeModals() {
    document.querySelectorAll('.modal').forEach(function (modal) {
      modal.hidden = true;
    });
    document.body.style.overflow = '';
  }

  document.querySelectorAll('[data-modal-close]').forEach(function (element) {
    element.addEventListener('click', closeModals);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') closeModals();
  });

  // --- Bildirishnoma (har 15 soniyada) -----------------------------------
  // Oddiy yopilsa (X, Escape, orqa fon) — keyingi 15 soniyada yana chiqadi.
  // Ariza yuborilganda forma sahifani to'liq qayta yuklaydi (server javobi
  // bilan), shuning uchun submit'ning o'zida hali natija (to'g'ri/xato)
  // ma'lum bo'lmaydi — shu sababli "yuborildi" belgisini keyingi sahifa
  // yuklanganda, faqat muvaffaqiyat xabari chiqqan bo'lsagina qo'yamiz.
  // Xato (noto'g'ri) ma'lumot kiritilsa — bildirishnoma davom etib chiqaveradi.
  const promo = document.querySelector('[data-promo]');
  const PROMO_KEY = 'sd-promo-submitted';
  const PROMO_PENDING_KEY = 'sd-promo-pending';

  if (sessionStorage.getItem(PROMO_PENDING_KEY) === '1') {
    sessionStorage.removeItem(PROMO_PENDING_KEY);
    if (document.querySelector('.flash.success')) {
      sessionStorage.setItem(PROMO_KEY, '1');
    }
  }

  if (promo && sessionStorage.getItem(PROMO_KEY) !== '1') {
    const timer = setInterval(function () {
      // Boshqa modal ochiq bo'lsa (masalan qo'ng'iroq so'rash) — xalaqit qilmaymiz.
      if (document.querySelector('.modal:not([hidden])')) return;
      promo.hidden = false;
      document.body.style.overflow = 'hidden';
    }, 15000);

    const promoForm = promo.querySelector('form');
    if (promoForm) {
      promoForm.addEventListener('submit', function () {
        sessionStorage.setItem(PROMO_PENDING_KEY, '1');
      });
    }
  }

  // --- Tungi rejim -------------------------------------------------------
  // Boshlang'ich qiymat base.html dagi inline skriptda qo'yiladi (chaqnashsiz)
  // va u doim aniq 'dark' yoki 'light' bo'ladi — shu sababli bu yerda faqat
  // atributni almashtirsak bo'ladi.
  const root = document.documentElement;
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)');
  const themeToggle = document.querySelector('[data-theme-toggle]');

  function currentTheme() {
    // Atribut yo'q bo'lsa (inline skript o'chib qolgan holat) — tizimga qaraymiz.
    const attr = root.getAttribute('data-theme');
    if (attr === 'dark' || attr === 'light') return attr;
    return systemDark.matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    if (themeToggle) {
      const dark = theme === 'dark';
      themeToggle.textContent = dark ? '☀' : '☾';
      themeToggle.setAttribute('aria-pressed', dark ? 'true' : 'false');
    }
  }

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      const next = currentTheme() === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      try { localStorage.setItem('sd-theme', next); } catch (e) { /* private mode */ }
    });
  }

  // Foydalanuvchi hali tanlamagan bo'lsa — tizim sozlamasi o'zgarsa, ergashamiz.
  systemDark.addEventListener('change', function (event) {
    let saved = null;
    try { saved = localStorage.getItem('sd-theme'); } catch (e) { /* private mode */ }
    if (saved !== 'dark' && saved !== 'light') applyTheme(event.matches ? 'dark' : 'light');
  });

  applyTheme(currentTheme());

  // --- Hero slayder ------------------------------------------------------
  // Slaydlar CSS'da bir katakda ustma-ust turadi, `.active` crossfade qiladi.
  const slider = document.querySelector('[data-slider]');
  if (slider) {
    const slides = Array.from(slider.querySelectorAll('.hero-slide'));
    const dots = Array.from(document.querySelectorAll('[data-slider-dots] .dot'));
    let index = slides.findIndex(function (slide) { return slide.classList.contains('active'); });
    let timer = null;
    if (index < 0) index = 0;

    function show(next) {
      index = (next + slides.length) % slides.length;
      slides.forEach(function (slide, i) {
        slide.classList.toggle('active', i === index);
      });
      dots.forEach(function (dot, i) {
        dot.classList.toggle('active', i === index);
        dot.setAttribute('aria-current', i === index ? 'true' : 'false');
      });
    }

    function start() {
      if (timer || slides.length < 2) return;
      timer = setInterval(function () { show(index + 1); }, 6000);
    }

    function stop() {
      clearInterval(timer);
      timer = null;
    }

    dots.forEach(function (dot) {
      dot.addEventListener('click', function () {
        show(Number(dot.dataset.index));
        stop();
        start();
      });
    });

    // Sichqoncha ustida turganda va tab ko'rinmaganda aylanish to'xtaydi.
    slider.addEventListener('mouseenter', stop);
    slider.addEventListener('mouseleave', start);
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stop(); else start();
    });

    start();
  }

  // --- Mahsulot galereyasi + lightbox ------------------------------------
  const galleryBox = document.querySelector('[data-gallery-main]');
  const galleryMain = galleryBox && galleryBox.querySelector('img');
  if (galleryMain) {
    const thumbs = Array.from(document.querySelectorAll('.thumb'));
    const sources = thumbs.map(function (thumb) { return thumb.dataset.src; });
    let current = 0;

    function swapTo(position) {
      current = (position + sources.length) % sources.length;
      galleryBox.classList.add('is-swapping');
      setTimeout(function () {
        galleryMain.src = sources[current];
        galleryBox.classList.remove('is-swapping');
      }, 180);
      thumbs.forEach(function (other, i) {
        other.classList.toggle('active', i === current);
      });
    }

    thumbs.forEach(function (thumb, i) {
      thumb.addEventListener('click', function () { swapTo(i); });
    });

    const lightbox = document.querySelector('[data-lightbox]');
    if (lightbox) {
      const big = lightbox.querySelector('img');

      function openLightbox() {
        big.src = sources.length ? sources[current] : galleryMain.src;
        lightbox.hidden = false;
        document.body.style.overflow = 'hidden';
      }

      function closeLightbox() {
        lightbox.hidden = true;
        document.body.style.overflow = '';
      }

      function step(delta) {
        if (!sources.length) return;
        swapTo(current + delta);
        big.src = sources[current];
      }

      galleryBox.addEventListener('click', openLightbox);
      lightbox.querySelectorAll('[data-lightbox-close]').forEach(function (element) {
        element.addEventListener('click', closeLightbox);
      });
      lightbox.querySelector('[data-lightbox-prev]').addEventListener('click', function (event) {
        event.stopPropagation();
        step(-1);
      });
      lightbox.querySelector('[data-lightbox-next]').addEventListener('click', function (event) {
        event.stopPropagation();
        step(1);
      });

      document.addEventListener('keydown', function (event) {
        if (lightbox.hidden) return;
        if (event.key === 'Escape') closeLightbox();
        if (event.key === 'ArrowLeft') step(-1);
        if (event.key === 'ArrowRight') step(1);
      });
    }
  }

  // --- Telefon maydoni -----------------------------------------------------
  // Avvalgi "focus'da +998 ni avtomatik yozish" olib tashlandi: foydalanuvchi
  // o'zi ham "+998" bilan boshlab yozganda ikkalasi qo'shilib
  // "+998 +998901234567" kabi buzuq qiymat hosil bo'lardi. Kutilgan format
  // endi faqat placeholder orqali ko'rsatiladi, maydonga hech narsa yozilmaydi.
})();
