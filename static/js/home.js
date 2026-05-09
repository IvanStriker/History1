(function () {
  var CATS = window.TRAIN_CATS || [];

  var overlay     = document.getElementById('train-modal-overlay');
  var form        = document.getElementById('train-form');
  var textInput   = document.getElementById('train-category-input');
  var hiddenInput = document.getElementById('train-category-value');
  var list        = document.getElementById('train-category-list');
  var catError    = document.getElementById('train-category-error');
  var modeRadios  = document.querySelectorAll('input[name="mode"]');
  var countField  = document.getElementById('train-count-field');
  var countInput  = document.getElementById('train-count');
  var countHint   = document.getElementById('train-count-hint');
  var cancelBtn   = document.getElementById('train-cancel-btn');
  var openBtn     = document.getElementById('btn-start-train');
  var tooltip     = document.getElementById('train-tooltip');

  var selectedCat = null;

  // ── Open / close modal ───────────────────

  if (openBtn) {
    openBtn.addEventListener('click', function (e) {
      e.preventDefault();
      overlay.classList.add('train-overlay--open');
    });
  }

  function closeModal() {
    overlay.classList.remove('train-overlay--open');
    closeList();
  }

  cancelBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeModal();
  });

  // ── Dropdown ─────────────────────────────

  function renderList(items) {
    list.innerHTML = '';
    if (!items.length) { closeList(); return; }
    items.forEach(function (cat) {
      var li = document.createElement('li');
      li.className = 'train-select__option';
      li.setAttribute('role', 'option');
      li.textContent = cat.name;
      li.addEventListener('mousedown', function (e) {
        e.preventDefault(); // prevents blur before click
        selectCat(cat);
      });
      li.addEventListener('mouseenter', function () {
        if (li.scrollWidth > li.clientWidth) {
          var rect = li.getBoundingClientRect();
          tooltip.textContent    = cat.name;
          tooltip.style.left     = rect.left + 'px';
          tooltip.style.top      = rect.top + 'px';
          tooltip.style.display  = 'block';
        }
      });
      li.addEventListener('mouseleave', function () {
        tooltip.style.display = 'none';
      });
      list.appendChild(li);
    });
    list.style.display = 'block';
  }

  function closeList() {
    list.style.display = 'none';
    tooltip.style.display = 'none';
  }

  function selectCat(cat) {
    selectedCat            = cat;
    textInput.value        = cat.name;
    hiddenInput.value      = cat.name;
    catError.style.display = 'none';
    closeList();
    updateCountMax();
  }

  textInput.addEventListener('focus', function () {
    var q        = textInput.value.trim().toLowerCase();
    var filtered = q ? CATS.filter(function (c) { return c.name.toLowerCase().indexOf(q) !== -1; }) : CATS;
    renderList(filtered);
  });

  textInput.addEventListener('input', function () {
    selectedCat            = null;
    hiddenInput.value      = '';
    var q        = textInput.value.trim().toLowerCase();
    var filtered = q ? CATS.filter(function (c) { return c.name.toLowerCase().indexOf(q) !== -1; }) : CATS;
    renderList(filtered);
  });

  textInput.addEventListener('blur', function () {
    setTimeout(function () {
      if (!selectedCat) {
        var val   = textInput.value.trim().toLowerCase();
        var match = null;
        for (var i = 0; i < CATS.length; i++) {
          if (CATS[i].name.toLowerCase() === val) { match = CATS[i]; break; }
        }
        if (match) {
          selectCat(match);
        } else {
          textInput.value   = '';
          hiddenInput.value = '';
        }
      }
      closeList();
    }, 150);
  });

  document.addEventListener('click', function (e) {
    var wrap = document.getElementById('train-select-wrap');
    if (wrap && !wrap.contains(e.target)) closeList();
  });

  // ── Mode ─────────────────────────────────

  modeRadios.forEach(function (radio) {
    radio.addEventListener('change', function () { updateCountState(); });
  });

  function getCurrentMode() {
    for (var i = 0; i < modeRadios.length; i++) {
      if (modeRadios[i].checked) return modeRadios[i].value;
    }
    return 'all';
  }

  function updateCountMax() {
    if (!selectedCat) { countHint.textContent = ''; return; }
    var max = Math.max(1, selectedCat.count);
    countInput.max = max;
    var cur = parseInt(countInput.value, 10);
    if (cur > max) countInput.value = max;
    if (cur < 1)   countInput.value = 1;
    countHint.textContent = selectedCat.count > 0
      ? 'от 1 до ' + selectedCat.count
      : 'в подборке нет карточек';
  }

  function updateCountState() {
    var random = getCurrentMode() === 'random';
    countInput.disabled = !random;
    countField.classList.toggle('train-field--disabled', !random);
  }

  // ── Submit ───────────────────────────────

  form.addEventListener('submit', function (e) {
    if (!hiddenInput.value) {
      e.preventDefault();
      catError.style.display = 'block';
      textInput.focus();
      return;
    }
    if (getCurrentMode() === 'random') {
      var v = parseInt(countInput.value, 10);
      if (!v || v < 1) {
        e.preventDefault();
        countInput.focus();
      }
    }
  });

})();
