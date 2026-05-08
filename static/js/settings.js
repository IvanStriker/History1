(function () {
  'use strict';

  var DEFAULTS = { textSize: 16, headingScale: 1.0 };

  var textSizeSlider    = document.getElementById('text-size');
  var headingSlider     = document.getElementById('heading-scale');
  var textSizeVal       = document.getElementById('text-size-val');
  var headingScaleVal   = document.getElementById('heading-scale-val');
  var previewHeading    = document.getElementById('preview-heading');
  var previewText       = document.getElementById('preview-text');
  var resetBtn          = document.getElementById('reset-btn');

  var textSize    = parseFloat(localStorage.getItem('setting_text_size'))    || DEFAULTS.textSize;
  var headingScale = parseFloat(localStorage.getItem('setting_heading_scale')) || DEFAULTS.headingScale;

  /* Инициализация слайдеров из localStorage */
  textSizeSlider.value = textSize;
  headingSlider.value  = Math.round(headingScale * 100);
  updateDisplay();

  /* Слушатели */
  textSizeSlider.addEventListener('input', function () {
    textSize = parseFloat(this.value);
    localStorage.setItem('setting_text_size', textSize);
    apply();
  });

  headingSlider.addEventListener('input', function () {
    headingScale = parseFloat(this.value) / 100;
    localStorage.setItem('setting_heading_scale', headingScale);
    apply();
  });

  resetBtn.addEventListener('click', function () {
    textSize     = DEFAULTS.textSize;
    headingScale = DEFAULTS.headingScale;
    localStorage.setItem('setting_text_size',    textSize);
    localStorage.setItem('setting_heading_scale', headingScale);
    textSizeSlider.value = textSize;
    headingSlider.value  = Math.round(headingScale * 100);
    apply();
  });

  function apply() {
    document.documentElement.style.fontSize = textSize + 'px';

    var style = document.getElementById('user-heading-style');
    if (style && window.__settingsBuildCSS) {
      style.textContent = window.__settingsBuildCSS(headingScale);
    }

    updateDisplay();
  }

  function updateDisplay() {
    textSizeVal.textContent     = textSize + ' px';
    headingScaleVal.textContent = Math.round(headingScale * 100) + '%';

    /* Заполненность трека слайдера */
    var textPct    = ((textSize - 12) / (22 - 12)) * 100;
    var headingPct = ((Math.round(headingScale * 100) - 70) / (150 - 70)) * 100;
    textSizeSlider.style.setProperty('--pct', textPct.toFixed(1) + '%');
    headingSlider.style.setProperty('--pct', headingPct.toFixed(1) + '%');

    /* Живой предпросмотр */
    previewText.style.fontSize    = textSize + 'px';
    previewHeading.style.fontSize = Math.round(textSize * 1.6 * headingScale) + 'px';
  }
}());
