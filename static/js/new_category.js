(function () {
  var chipsEl    = document.getElementById('card-chips');
  var listEl     = document.getElementById('card-list');
  var searchEl   = document.getElementById('card-search');
  var hiddenWrap = document.getElementById('card-hidden-inputs');

  if (!chipsEl || !listEl) return;

  var selected = {};

  // ── Восстановить предвыбранные (режим редактирования) ──
  var preInputs = hiddenWrap.querySelectorAll('input[data-preselected]');
  preInputs.forEach(function (inp) {
    var id      = parseInt(inp.value, 10);
    var text    = inp.dataset.text || ('#' + id);
    var isImage = inp.dataset.isImage === '1';
    selected[id] = text;
    markItemSelected(id, true);
    renderChip(id, text, isImage);
  });

  // ── Кнопка «+» в списке карточек ──────────
  listEl.addEventListener('click', function (e) {
    var btn = e.target.closest('.card-picker__add-btn');
    if (!btn) return;
    var item = btn.closest('.card-picker__item');
    if (!item) return;
    var id      = parseInt(item.dataset.id, 10);
    var text    = item.dataset.text || ('#' + id);
    var isImage = item.dataset.isImage === '1';
    if (selected[id]) return;
    selected[id] = text;
    addHiddenInput(id);
    renderChip(id, text, isImage);
    markItemSelected(id, true);
  });

  // ── Кнопка «×» на чипсе ───────────────────
  chipsEl.addEventListener('click', function (e) {
    var btn = e.target.closest('.card-picker__chip-remove');
    if (!btn) return;
    var id = parseInt(btn.dataset.id, 10);
    delete selected[id];
    var inp = hiddenWrap.querySelector('input[value="' + id + '"]');
    if (inp) inp.remove();
    var chip = chipsEl.querySelector('.card-picker__chip[data-id="' + id + '"]');
    if (chip) chip.remove();
    markItemSelected(id, false);
  });

  // ── Поиск по всем полям ───────────────────
  if (searchEl) {
    searchEl.addEventListener('input', function () {
      var q = this.value.toLowerCase().trim();
      listEl.querySelectorAll('.card-picker__item').forEach(function (item) {
        var front  = (item.dataset.front  || '').toLowerCase();
        var back   = (item.dataset.back   || '').toLowerCase();
        var answer = (item.dataset.answer || '').toLowerCase();
        var match  = !q || front.includes(q) || back.includes(q) || answer.includes(q);
        item.style.display = match ? '' : 'none';
      });
    });
  }

  // ── Вспомогательные функции ────────────────
  function addHiddenInput(id) {
    var old = hiddenWrap.querySelector('input[value="' + id + '"]');
    if (old) old.remove();
    var inp = document.createElement('input');
    inp.type  = 'hidden';
    inp.name  = 'card_ids[]';
    inp.value = id;
    hiddenWrap.appendChild(inp);
  }

  function renderChip(id, text, isImage) {
    var chip = document.createElement('span');
    chip.className  = 'card-picker__chip';
    chip.dataset.id = id;
    var iconHtml = isImage
      ? '<svg class="card-picker__chip-img-icon" viewBox="0 0 16 16" aria-hidden="true">' +
        '<rect x="1" y="2" width="14" height="12" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.2"/>' +
        '<circle cx="5.5" cy="6.5" r="1.2" fill="currentColor"/>' +
        '<path d="M1.5 11.5l3.5-3.5 2.5 2.5 2-2 4 4" stroke="currentColor" stroke-width="1.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' +
        '</svg>'
      : '';
    chip.innerHTML  =
      iconHtml +
      '<span class="card-picker__chip-text">' + escHtml(text) + '</span>' +
      '<button type="button" class="card-picker__chip-remove" data-id="' + id + '" aria-label="Убрать">×</button>';
    chipsEl.appendChild(chip);
  }

  function markItemSelected(id, yes) {
    var item = listEl.querySelector('.card-picker__item[data-id="' + id + '"]');
    if (!item) return;
    if (yes) item.classList.add('card-picker__item--selected');
    else     item.classList.remove('card-picker__item--selected');
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
})();
