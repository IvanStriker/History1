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
    var id   = parseInt(inp.value, 10);
    var text = inp.dataset.text || ('#' + id);
    selected[id] = text;
    markItemSelected(id, true);
    renderChip(id, text);
  });

  // ── Кнопка «+» в списке карточек ──────────
  listEl.addEventListener('click', function (e) {
    var btn = e.target.closest('.card-picker__add-btn');
    if (!btn) return;
    var item = btn.closest('.card-picker__item');
    if (!item) return;
    var id   = parseInt(item.dataset.id, 10);
    var text = item.dataset.text || ('#' + id);
    if (selected[id]) return;
    selected[id] = text;
    addHiddenInput(id);
    renderChip(id, text);
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

  // ── Поиск ─────────────────────────────────
  if (searchEl) {
    searchEl.addEventListener('input', function () {
      var q = this.value.toLowerCase().trim();
      listEl.querySelectorAll('.card-picker__item').forEach(function (item) {
        var text = (item.dataset.text || '').toLowerCase();
        item.style.display = (!q || text.includes(q)) ? '' : 'none';
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

  function renderChip(id, text) {
    var chip = document.createElement('span');
    chip.className  = 'card-picker__chip';
    chip.dataset.id = id;
    chip.innerHTML  =
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
