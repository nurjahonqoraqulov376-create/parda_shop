/* Boshqaruv panelidagi AI yordamchi.
 *
 * Sahifa yangilanmasdan ishlaydi, lekin ma'lumot bazaga faqat
 * TASDIQLASH tugmasi bosilganda yoziladi — u oddiy POST forma
 * (`dashboard:agent_run`). Bu yerda hech qanday yozish yo'q.
 */
(function () {
  'use strict';

  var root = document.querySelector('[data-agent]');
  if (!root) { return; }

  var form = root.querySelector('[data-agent-form]');
  var input = root.querySelector('[data-agent-input]');
  var log = root.querySelector('[data-agent-log]');
  var proposal = root.querySelector('[data-agent-proposal]');
  var proposalText = root.querySelector('[data-agent-proposal-text]');
  var imageInput = root.querySelector('[data-agent-image]');
  var picked = root.querySelector('[data-agent-picked]');
  var pickedPreview = root.querySelector('[data-agent-picked-preview]');
  var pickedName = root.querySelector('[data-agent-picked-name]');
  var pickedDrop = root.querySelector('[data-agent-picked-drop]');
  var sendUrl = root.dataset.urlSend;
  var pulseUrl = root.dataset.urlPulse;
  var errorText = root.dataset.textError || 'Xato';
  var busy = false;

  function token() {
    // Cookie'dagi qiymat doim joriy; formadagisi kirishdan keyin eskiradi.
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    if (match) { return decodeURIComponent(match[1]); }
    var field = root.querySelector('[name=csrfmiddlewaretoken]');
    return field ? field.value : '';
  }

  function bubble(role, text) {
    var row = document.createElement('div');
    row.className = 'ag-row ag-' + role;
    var body = document.createElement('div');
    body.className = 'ag-bubble';
    // `textContent` — javob matni HTML sifatida talqin qilinmasin.
    body.textContent = text;
    row.appendChild(body);
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
    return row;
  }

  function showProposal(action) {
    if (!proposal) { return; }
    if (action) {
      proposalText.textContent = action.summary;
      proposal.hidden = false;
    } else {
      proposal.hidden = true;
    }
  }

  // --- Biriktirilgan rasm ---
  function clearPicked() {
    if (imageInput) { imageInput.value = ''; }
    if (picked) { picked.hidden = true; }
    if (pickedPreview && pickedPreview.src.indexOf('blob:') === 0) {
      URL.revokeObjectURL(pickedPreview.src);
      pickedPreview.removeAttribute('src');
    }
  }

  if (imageInput) {
    imageInput.addEventListener('change', function () {
      var file = imageInput.files && imageInput.files[0];
      if (!file) { clearPicked(); return; }
      if (pickedPreview) { pickedPreview.src = URL.createObjectURL(file); }
      if (pickedName) { pickedName.textContent = file.name; }
      if (picked) { picked.hidden = false; }
    });
  }
  if (pickedDrop) { pickedDrop.addEventListener('click', clearPicked); }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (busy) { return; }

    var text = (input.value || '').trim();
    var file = imageInput && imageInput.files ? imageInput.files[0] : null;
    // Rasm bo'lsa matnsiz ham yuborish mumkin.
    if (!text && !file) { return; }

    busy = true;
    input.value = '';
    bubble('user', text || (file ? '📎 ' + file.name : ''));
    var waiting = bubble('agent', '…');

    var body = new FormData();
    body.append('csrfmiddlewaretoken', token());
    body.append('text', text);
    if (file) { body.append('image', file); }
    clearPicked();

    fetch(sendUrl, {
      method: 'POST',
      body: body,
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        waiting.querySelector('.ag-bubble').textContent = data.answer || data.error || errorText;
        showProposal(data.action);
        if (data.has_image && proposal && !proposal.hidden) {
          proposal.classList.add('has-image');
        }
      })
      .catch(function () {
        waiting.querySelector('.ag-bubble').textContent = errorText;
      })
      .then(function () {
        busy = false;
        log.scrollTop = log.scrollHeight;
      });
  });

  // Enter — yuborish, Shift+Enter — yangi qator.
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit'));
    }
  });

  // ---- Nazorat qatorini yangilab turish ----
  var alertsBox = document.querySelector('[data-agent-alerts]');
  if (alertsBox && pulseUrl) {
    setInterval(function () {
      // Sahifa ko'rinmayotgan bo'lsa so'rov yubormaymiz (trafik va batareya).
      if (document.hidden) { return; }
      fetch(pulseUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (!data || !data.alerts) { return; }
          alertsBox.textContent = '';
          data.alerts.forEach(function (alert) {
            var item = document.createElement('li');
            item.className = 'ag-alert ag-' + alert.level;
            item.textContent = alert.text;
            alertsBox.appendChild(item);
          });
        })
        .catch(function () { /* tarmoq uzildi — keyingi urinishda */ });
    }, 60000);
  }
})();
