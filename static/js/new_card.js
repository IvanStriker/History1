(function () {
  function bindTypeToggle(radioName, textareaId) {
    document.querySelectorAll('input[name="' + radioName + '"]').forEach(function (r) {
      r.addEventListener('change', function () {
        var ta = document.getElementById(textareaId);
        if (ta) ta.placeholder = r.value === 'image' ? 'Путь к изображению...' : 'Введите текст...';
      });
    });
  }
  bindTypeToggle('front_type', 'front_content');
  bindTypeToggle('back_type',  'back_content');
})();
