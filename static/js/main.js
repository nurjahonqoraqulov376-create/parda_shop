// Sevara Design — sayt interfeysi uchun kichik vanilla JS

(function () {
  'use strict';

  // --- Sahifa surilishini qulflash (modal ochiq turganda) ----------------
  // iOS Safari'da `body { overflow: hidden }` yetarli emas: modal ochiq
  // bo'lsa ham orqa fon barmoq bilan surilib ketaverardi. Shu sababli
  // sahifani `position: fixed` bilan joyida ushlab turamiz va yopilganda
  // avvalgi joyiga qaytaramiz.
  let lockedScrollY = 0;
  let lockCount = 0;

  function lockScroll() {
    if (lockCount++ > 0) return;
    lockedScrollY = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = -lockedScrollY + 'px';
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
  }

  function unlockScroll() {
    if (lockCount === 0) return;
    lockCount = 0;
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    document.body.style.width = '';
    window.scrollTo(0, lockedScrollY);
  }

  // --- Mobil menyu -------------------------------------------------------
  const menuToggle = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('[data-menu]');

  function setMenu(open) {
    if (!menu) return;
    menu.classList.toggle('open', open);
    if (menuToggle) menuToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  if (menuToggle && menu) {
    menuToggle.setAttribute('aria-expanded', 'false');
    menuToggle.addEventListener('click', function (event) {
      event.stopPropagation();
      setMenu(!menu.classList.contains('open'));
    });

    // Menyudan tashqariga bosilsa yopiladi — telefonda menyu ochiq qolib,
    // sahifani to'sib turardi.
    document.addEventListener('click', function (event) {
      if (menu.classList.contains('open') && !menu.contains(event.target)) setMenu(false);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') setMenu(false);
    });
  }

  // --- Katalog ostki ro'yxati (telefonda bosish bilan ochiladi) ----------
  // Sensorli ekranda `:hover` ishlamaydi: «Katalog» ustiga bosilganda ostki
  // ro'yxat ochilmasdan darhol katalog sahifasiga o'tib ketardi, ya'ni
  // kategoriyalar menyusi telefonda umuman ochilmasdi. Endi strelka
  // ro'yxatni ochadi, matnning o'zi esa avvalgidek katalogga o'tkazadi.
  document.querySelectorAll('.has-mega').forEach(function (block) {
    const caret = block.querySelector('.caret');
    if (!caret) return;
    caret.setAttribute('role', 'button');
    caret.setAttribute('tabindex', '0');
    caret.setAttribute('aria-expanded', 'false');

    function toggleMega(event) {
      // Faqat mobil ko'rinishda — kattaroq ekranda `:hover` o'z ishini qiladi.
      if (!window.matchMedia('(max-width: 900px)').matches) return;
      event.preventDefault();
      event.stopPropagation();
      const open = !block.classList.contains('is-open');
      block.classList.toggle('is-open', open);
      caret.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    caret.addEventListener('click', toggleMega);
    caret.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') toggleMega(event);
    });
  });

  // --- Modal (qo'ng'iroq so'rash) ----------------------------------------
  document.querySelectorAll('[data-modal-open]').forEach(function (button) {
    button.addEventListener('click', function () {
      const modal = document.getElementById('modal-' + button.dataset.modalOpen);
      if (modal) {
        modal.hidden = false;
        lockScroll();
      }
    });
  });

  function closeModals() {
    document.querySelectorAll('.modal').forEach(function (modal) {
      modal.hidden = true;
    });
    unlockScroll();
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

  // Ilgari bildirishnoma har 15 soniyada qayta chiqardi va sahifa surilishini
  // qulflardi — telefonda o'qishga imkon bermasdi. Endi bir seansda bir marta,
  // 25 soniyadan keyin chiqadi. Chastotani shu yerdan o'zgartirish mumkin.
  const PROMO_DELAY = 25000;

  if (promo && sessionStorage.getItem(PROMO_KEY) !== '1') {
    setTimeout(function showPromo() {
      // Boshqa modal ochiq bo'lsa (masalan qo'ng'iroq so'rash) — xalaqit
      // qilmaymiz, biroz kutib qayta urinamiz.
      if (document.querySelector('.modal:not([hidden])')) {
        setTimeout(showPromo, 5000);
        return;
      }
      promo.hidden = false;
      lockScroll();
      // Bir marta ko'rsatdik — shu seansda boshqa bezovta qilmaymiz.
      try { sessionStorage.setItem(PROMO_KEY, '1'); } catch (e) { /* private mode */ }
    }, PROMO_DELAY);

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

    // Telefonda barmoq bilan surib slayd almashtirish. Vertikal surish
    // (sahifani aylantirish) buzilmasligi uchun faqat aniq gorizontal
    // harakatga javob beramiz.
    let touchX = null;
    let touchY = null;
    slider.addEventListener('touchstart', function (event) {
      const point = event.changedTouches[0];
      touchX = point.clientX;
      touchY = point.clientY;
      stop();
    }, { passive: true });

    slider.addEventListener('touchend', function (event) {
      if (touchX === null) return;
      const point = event.changedTouches[0];
      const deltaX = point.clientX - touchX;
      const deltaY = point.clientY - touchY;
      touchX = touchY = null;
      if (Math.abs(deltaX) > 45 && Math.abs(deltaX) > Math.abs(deltaY)) {
        show(index + (deltaX < 0 ? 1 : -1));
      }
      start();
    }, { passive: true });
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
        lockScroll();
      }

      function closeLightbox() {
        lightbox.hidden = true;
        unlockScroll();
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
