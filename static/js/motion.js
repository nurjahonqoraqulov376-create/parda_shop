// Sevara Design — skroll va kursor animatsiyalari.
// main.js UI mexanikasi (menyu, modal, slayder) bilan shug'ullanadi, bu fayl faqat harakat.

(function () {
  'use strict';

  const root = document.documentElement;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Harakat so'ralmagan bo'lsa hech narsa qilmaymiz — kontent oddiy holicha ko'rinadi.
  if (reduced || !('IntersectionObserver' in window)) {
    root.setAttribute('data-motion', 'off');
    return;
  }
  root.setAttribute('data-motion', 'on');

  const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  // --- Skroll reveal -----------------------------------------------------
  // Shablonlarga atribut yozmaymiz: mavjud klasslarni shu yerda belgilaymiz.
  const REVEAL = '.section-head, .page-head .wrap, .stats-grid, .seo-block, .form-card, .lead-form';
  const GROUPS = ['.cat-grid', '.grid-3', '.grid-4', '.rail', '.adv-grid', '.tst-grid', '.client-row', '.faq', '.branch-grid'];

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      observer.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -12% 0px', threshold: .12 });

  function watch(element, index) {
    element.classList.add('reveal');
    if (index) element.style.setProperty('--i', index);
    observer.observe(element);
  }

  document.querySelectorAll(REVEAL).forEach(function (element) { watch(element, 0); });

  // Grid bolalari ketma-ket chiqadi (--i orqali kechikish).
  GROUPS.forEach(function (selector) {
    document.querySelectorAll(selector).forEach(function (grid) {
      Array.prototype.forEach.call(grid.children, function (child, i) {
        watch(child, Math.min(i, 7));
      });
    });
  });

  // Bo'limning o'zi ham kuzatiladi — sarlavha ostidagi aksent chiziq uchun.
  document.querySelectorAll('.section').forEach(function (section) {
    observer.observe(section);
  });

  // --- Raqam sanagich ----------------------------------------------------
  const counters = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      countUp(entry.target);
      counters.unobserve(entry.target);
    });
  }, { threshold: .5 });

  document.querySelectorAll('[data-count]').forEach(function (element) {
    counters.observe(element);
  });

  function countUp(element) {
    const target = Number(element.dataset.count) || 0;
    const suffix = element.dataset.countSuffix || '';
    const duration = 1400;
    const start = performance.now();

    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4); // easeOutQuart
      element.textContent = Math.round(target * eased) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // --- Skroll: progress chizig'i, header holati, hero parallaks ----------
  const progress = document.querySelector('[data-scroll-progress]');
  const header = document.querySelector('.header');
  let ticking = false;

  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      const y = window.scrollY;

      if (progress) {
        const max = document.documentElement.scrollHeight - window.innerHeight;
        progress.style.transform = 'scaleX(' + (max > 0 ? y / max : 0) + ')';
      }
      if (header) header.classList.toggle('is-stuck', y > 40);

      // Hero rasmi sahifadan sekinroq siljiydi.
      const media = document.querySelector('.hero-slide.active .hero-media');
      if (media && y < window.innerHeight) {
        media.style.transform = 'translate3d(0,' + (y * 0.12).toFixed(1) + 'px,0)';
      }

      ticking = false;
    });
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // --- Hero sarlavhasi: so'zlar birma-bir ko'tariladi --------------------
  const heroTitle = document.querySelector('.hero-slide.active .hero-text h1');
  if (heroTitle && !heroTitle.dataset.split) {
    heroTitle.dataset.split = '1';
    const words = heroTitle.textContent.trim().split(/\s+/);
    heroTitle.textContent = '';
    words.forEach(function (word, i) {
      const span = document.createElement('span');
      span.textContent = word;
      span.style.cssText = 'display:inline-block;opacity:0;transform:translateY(20px);' +
        'transition:opacity .6s cubic-bezier(.16,1,.3,1) ' + (i * 70) + 'ms,' +
        'transform .6s cubic-bezier(.16,1,.3,1) ' + (i * 70) + 'ms';
      heroTitle.appendChild(span);
      if (i < words.length - 1) heroTitle.appendChild(document.createTextNode(' '));
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          span.style.opacity = '1';
          span.style.transform = 'none';
        });
      });
    });
  }

  // --- 3D tilt + kursor ortidagi yorug'lik ------------------------------
  // Faqat sichqoncha bor qurilmalarda — sensorli ekranda umuman yoqilmaydi.
  if (fine) {
    document.querySelectorAll('.card, .cat-tile').forEach(function (element) {
      element.classList.add('tilt');
      let raf = null;

      element.addEventListener('pointermove', function (event) {
        if (raf) return;
        raf = requestAnimationFrame(function () {
          const box = element.getBoundingClientRect();
          const px = (event.clientX - box.left) / box.width;
          const py = (event.clientY - box.top) / box.height;
          element.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
          element.style.setProperty('--my', (py * 100).toFixed(1) + '%');
          element.style.transform =
            'perspective(900px) rotateX(' + ((0.5 - py) * 6).toFixed(2) + 'deg) ' +
            'rotateY(' + ((px - 0.5) * 6).toFixed(2) + 'deg) translateY(-6px)';
          raf = null;
        });
      });

      element.addEventListener('pointerleave', function () {
        element.style.transform = '';
      });
    });
  }

  // --- Sahifalar orasidagi yumshoq o'tish -------------------------------
  document.addEventListener('click', function (event) {
    const link = event.target.closest('a');
    if (!link) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    if (link.target === '_blank' || link.hasAttribute('download')) return;

    const href = link.getAttribute('href') || '';
    if (!href || href.charAt(0) === '#' || href.indexOf('mailto:') === 0 || href.indexOf('tel:') === 0) return;
    if (link.host !== window.location.host) return;
    if (link.pathname === window.location.pathname && link.search === window.location.search) return;

    document.body.classList.add('is-leaving');
  });

  // Orqaga qaytilganda sahifa ko'rinmay qolmasligi uchun.
  window.addEventListener('pageshow', function () {
    document.body.classList.remove('is-leaving');
  });
})();
