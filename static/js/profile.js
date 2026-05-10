(function () {
  var overlay   = document.getElementById('profile-settings-overlay');
  var openBtn   = document.getElementById('settingsOpenBtn');
  var cancelBtn = document.getElementById('settingsCancelBtn');
  var form      = document.getElementById('profile-settings-form');
  var errorEl   = document.getElementById('ps-error');

  if (!overlay || !openBtn) return;

  function openModal() {
    overlay.classList.add('ps-overlay--open');
    overlay.querySelector('.ps-form__input').focus();
  }

  function closeModal() {
    overlay.classList.remove('ps-overlay--open');
    if (errorEl) errorEl.textContent = '';
  }

  openBtn.addEventListener('click', openModal);
  cancelBtn.addEventListener('click', closeModal);

  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeModal();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (errorEl) errorEl.textContent = '';

    var data = {
      first_name:       form.querySelector('[name="first_name"]').value.trim(),
      last_name:        form.querySelector('[name="last_name"]').value.trim(),
      username:         form.querySelector('[name="username"]').value.trim(),
      email:            form.querySelector('[name="email"]').value.trim(),
      bio:              form.querySelector('[name="bio"]').value.trim(),
      new_password:     form.querySelector('[name="new_password"]').value,
      confirm_password: form.querySelector('[name="confirm_password"]').value,
    };

    fetch('/api/profile/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      if (resp.ok) {
        closeModal();
        window.location.reload();
      } else {
        if (errorEl) errorEl.textContent = resp.error || 'Ошибка при сохранении.';
      }
    })
    .catch(function () {
      if (errorEl) errorEl.textContent = 'Сетевая ошибка.';
    });
  });
})();
