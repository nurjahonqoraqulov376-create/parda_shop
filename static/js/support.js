// Sevara Design — saytdagi suhbat oynasi (support chat)

(function () {
  'use strict';

  const root = document.querySelector('[data-support]');
  if (!root) return;

  const toggles = root.querySelectorAll('[data-support-toggle]');
  const panel = root.querySelector('.sc-panel');
  const log = root.querySelector('[data-support-log]');
  const form = root.querySelector('[data-support-form]');
  const input = root.querySelector('[data-support-input]');
  const sendButton = root.querySelector('.sc-send');
  const statusLine = root.querySelector('[data-support-status]');

  const urlSend = root.dataset.urlSend;
  const urlHistory = root.dataset.urlHistory;
  const textFailed = root.dataset.textFailed || 'Xatolik';
  const textWaiting = root.dataset.textWaiting || '';
  const textConnected = root.dataset.textConnected || '';
  const textSubtitle = statusLine ? statusLine.textContent.trim() : '';
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;

  // Yangi xabarlarni tekshirish oralig'i. Oyna yopiq bo'lsa so'rov ketmaydi.
  const POLL_MS = 4000;
  let lastId = 0;
  let timer = null;
  let sending = false;

  // --- Ko'rsatish -----------------------------------------------------------
  function lastRow() {
    return log.querySelector('.sc-row:last-child');
  }

  function addMessage(message, pending) {
    // Server qaytargan xabar id bilan keladi; bir xil id ikki marta
    // qo'shilmasin (polling va javob bir vaqtda kelishi mumkin).
    if (message.id) {
      if (message.id <= lastId) return;
      lastId = message.id;
    }

    const row = document.createElement('div');
    row.className = 'sc-row sc-' + message.sender;
    if (pending) row.dataset.pending = '1';

    // Ketma-ket kelgan bir xil yuboruvchi xabarlari yaqinroq turadi.
    const previous = lastRow();
    if (previous && previous.classList.contains('sc-' + message.sender)) {
      row.classList.add('sc-grouped');
    }

    const bubble = document.createElement('div');
    bubble.className = 'sc-bubble';
    // textContent — matn HTML sifatida talqin qilinmaydi (XSS bo'lmasin).
    bubble.textContent = message.text;
    row.appendChild(bubble);

    if (message.time) {
      const time = document.createElement('time');
      time.textContent = message.time;
      row.appendChild(time);
    }

    log.appendChild(row);
    scrollToEnd();
  }

  function dropPending() {
    log.querySelectorAll('[data-pending]').forEach(function (row) { row.remove(); });
  }

  function scrollToEnd() {
    log.scrollTop = log.scrollHeight;
  }

  function setStatus(payload) {
    if (!payload || !statusLine) return;
    root.classList.toggle('is-waiting', payload.status === 'waiting_operator');
    root.classList.toggle('is-live', payload.status === 'with_operator');
    if (payload.status === 'waiting_operator' && textWaiting) {
      statusLine.textContent = textWaiting;
    } else if (payload.status === 'with_operator' && textConnected) {
      statusLine.textContent = textConnected;
    } else {
      statusLine.textContent = textSubtitle;
    }
  }

  // «Yozmoqda…» — haqiqiy pufakcha, xabarlar oqimida ko'rinadi.
  function showTyping(on) {
    const existing = log.querySelector('.sc-typing');
    if (!on) {
      if (existing) existing.remove();
      return;
    }
    if (existing) return;
    const row = document.createElement('div');
    row.className = 'sc-row sc-ai sc-typing';
    row.innerHTML = '<div class="sc-bubble"><span></span><span></span><span></span></div>';
    log.appendChild(row);
    scrollToEnd();
  }

  function syncSendButton() {
    if (sendButton) sendButton.disabled = !input.value.trim() || sending;
  }

  // --- Server bilan aloqa ---------------------------------------------------
  function poll() {
    fetch(urlHistory + '?after=' + lastId, { credentials: 'same-origin' })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (payload) {
        if (!payload) return;
        (payload.messages || []).forEach(function (message) { addMessage(message); });
        setStatus(payload);
      })
      .catch(function () { /* tarmoq uzildi — keyingi urinishda davom etadi */ });
  }

  function startPolling() {
    if (timer) return;
    timer = setInterval(function () {
      if (!document.hidden) poll();
    }, POLL_MS);
  }

  function stopPolling() {
    clearInterval(timer);
    timer = null;
  }

  function send(text) {
    if (sending) return;
    sending = true;
    syncSendButton();
    showTyping(true);

    const body = new URLSearchParams();
    body.set('text', text);

    fetch(urlSend, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrf,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: body.toString(),
    })
      .then(function (response) {
        return response.json().then(function (data) { return { ok: response.ok, data: data }; });
      })
      .then(function (result) {
        showTyping(false);
        if (!result.ok) {
          // Vaqtinchalik pufakchani qoldiramiz — xabar yuborilmadi, lekin
          // foydalanuvchi nima yozganini ko'rib tursin.
          addMessage({ sender: 'system', text: result.data.error || textFailed });
          return;
        }
        // Server aynan shu xabarni id bilan qaytaradi — vaqtinchalik
        // pufakchani olib tashlaymiz, aks holda xabar ikki marta ko'rinadi.
        dropPending();
        (result.data.messages || []).forEach(function (message) { addMessage(message); });
        setStatus(result.data);
      })
      .catch(function () {
        showTyping(false);
        addMessage({ sender: 'system', text: textFailed });
      })
      .finally(function () {
        sending = false;
        syncSendButton();
      });
  }

  // --- Ochish / yopish ------------------------------------------------------
  function setOpen(open) {
    panel.hidden = !open;
    root.classList.toggle('is-open', open);
    toggles.forEach(function (button) {
      if (button.hasAttribute('aria-expanded')) {
        button.setAttribute('aria-expanded', open ? 'true' : 'false');
      }
    });
    if (open) {
      poll();
      startPolling();
      scrollToEnd();
      // Telefonda klaviatura darhol ochilib ketmasin — faqat kattaroq ekranda.
      if (window.matchMedia('(min-width: 561px)').matches) input.focus();
    } else {
      stopPolling();
    }
  }

  toggles.forEach(function (button) {
    button.addEventListener('click', function () { setOpen(panel.hidden); });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !panel.hidden) setOpen(false);
  });

  // --- Yuborish -------------------------------------------------------------
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || sending) return;
    // Darhol ko'rsatamiz (kutish sezilmasin), serverdan javob kelgach
    // haqiqiysi bilan almashtiriladi.
    addMessage({ sender: 'visitor', text: text }, true);
    input.value = '';
    input.style.height = '';
    syncSendButton();
    send(text);
  });

  // Enter — yuborish, Shift+Enter — yangi qator.
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (form.requestSubmit) form.requestSubmit();
      else form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  });

  // Maydon yozilgan matnga qarab o'ssin (lekin cheklangan balandlikda).
  input.addEventListener('input', function () {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 110) + 'px';
    syncSendButton();
  });

  document.addEventListener('visibilitychange', function () {
    if (!panel.hidden && !document.hidden) poll();
  });

  syncSendButton();
})();
