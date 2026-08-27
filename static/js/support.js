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
  const statusLine = root.querySelector('[data-support-status]');

  const urlSend = root.dataset.urlSend;
  const urlHistory = root.dataset.urlHistory;
  const textFailed = root.dataset.textFailed || 'Xatolik';
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;

  // Yangi xabarlarni tekshirish oralig'i. Oyna yopiq bo'lsa so'rov ketmaydi.
  const POLL_MS = 4000;
  let lastId = 0;
  let timer = null;
  let sending = false;

  // --- Ko'rsatish -----------------------------------------------------------
  function addMessage(message) {
    if (message.id && message.id <= lastId) return;
    if (message.id) lastId = message.id;

    const row = document.createElement('div');
    row.className = 'sc-msg sc-' + message.sender;
    const text = document.createElement('p');
    // textContent — HTML sifatida talqin qilinmaydi (XSS bo'lmasin).
    text.textContent = message.text;
    row.appendChild(text);
    if (message.time) {
      const time = document.createElement('time');
      time.textContent = message.time;
      row.appendChild(time);
    }
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  function setStatus(payload) {
    if (!statusLine) return;
    if (payload.status === 'waiting_operator') {
      statusLine.textContent = statusLine.dataset.waiting || '⏳';
      root.classList.add('is-waiting');
    } else if (payload.status === 'with_operator') {
      root.classList.remove('is-waiting');
      root.classList.add('is-live');
    }
  }

  function showTyping(on) {
    root.classList.toggle('is-typing', on);
  }

  // --- Server bilan aloqa ---------------------------------------------------
  function poll() {
    fetch(urlHistory + '?after=' + lastId, { credentials: 'same-origin' })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (payload) {
        if (!payload) return;
        (payload.messages || []).forEach(addMessage);
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
      .then(function (response) { return response.json().then(function (data) { return { ok: response.ok, data: data }; }); })
      .then(function (result) {
        if (!result.ok) {
          addMessage({ sender: 'system', text: result.data.error || textFailed });
          return;
        }
        (result.data.messages || []).forEach(addMessage);
        setStatus(result.data);
      })
      .catch(function () {
        addMessage({ sender: 'system', text: textFailed });
      })
      .finally(function () {
        sending = false;
        showTyping(false);
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
    if (!text) return;
    addMessage({ sender: 'visitor', text: text });
    input.value = '';
    input.style.height = '';
    send(text);
  });

  // Enter — yuborish, Shift+Enter — yangi qator.
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  });

  // Maydon yozilgan matnga qarab o'ssin (lekin cheklangan balandlikda).
  input.addEventListener('input', function () {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });

  document.addEventListener('visibilitychange', function () {
    if (!panel.hidden && !document.hidden) poll();
  });
})();
