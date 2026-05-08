/* Применяет сохранённые настройки шрифтов сразу при загрузке страницы.
   Подключается в <head> всех страниц до загрузки CSS. */
(function () {
  'use strict';

  var textSize    = parseFloat(localStorage.getItem('setting_text_size'))    || 16;
  var headingScale = parseFloat(localStorage.getItem('setting_heading_scale')) || 1.0;

  /* Масштабирует всё rem-зависимое (основной текст, кнопки, бейджи) */
  document.documentElement.style.fontSize = textSize + 'px';

  /* Дополнительный множитель для заголовков */
  var s = document.createElement('style');
  s.id  = 'user-heading-style';
  s.textContent = buildCSS(headingScale);
  document.head.appendChild(s);

  function buildCSS(hs) {
    return (
      '.site-title{font-size:calc(clamp(2.4rem,7vw,4.2rem)*' + hs + ')!important}' +
      '.cards-header__title{font-size:calc(1.5rem*' + hs + ')!important}' +
      'h1:not(.site-title):not(.cards-header__title){font-size:calc(1.8rem*' + hs + ')!important}' +
      'h2:not(.preview-heading){font-size:calc(1.4rem*' + hs + ')!important}' +
      'h3{font-size:calc(1.2rem*' + hs + ')!important}'
    );
  }

  /* Экспортируем buildCSS для settings.js */
  window.__settingsBuildCSS = buildCSS;
}());
