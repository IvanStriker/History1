/**
 * train.js — Полная игровая логика страницы /train
 *
 * Архитектура:
 *  ┌─────────────────────────────────────────────────────────┐
 *  │  EventBus (Phaser.Events.EventEmitter)                  │
 *  │   — единая шина событий между DOM-логикой и Phaser-сценой│
 *  ├─────────────────────────────────────────────────────────┤
 *  │  CardScene (Phaser.Scene)                               │
 *  │   — рендерит карточку, анимирует переворот,             │
 *  │     рисует glow-эффект при правильном/неправильном ответе│
 *  ├─────────────────────────────────────────────────────────┤
 *  │  DOM-логика (внизу файла)                               │
 *  │   — читает данные из атрибутов <body> (Jinja2),         │
 *  │     управляет счётчиками, навигацией, вводом ответа     │
 *  └─────────────────────────────────────────────────────────┘
 *
 * API, которое ожидается от сервера:
 *   GET /card?id=X
 *   → {
 *       id:   number,
 *       front: { type: 'text'|'image', content: string },
 *       back:  { type: 'text'|'image', content: string, answer_text: string }
 *     }
 *   Поле answer_text ВСЕГДА строка — используется для сравнения с вводом пользователя.
 */

'use strict';

/* ═══════════════════════════════════════════════════════════════
   1. ШИНА СОБЫТИЙ
   ═══════════════════════════════════════════════════════════════ */
const EventBus = new Phaser.Events.EventEmitter();

/* ═══════════════════════════════════════════════════════════════
   2. КОНСТАНТЫ КАРТОЧКИ
   ═══════════════════════════════════════════════════════════════ */
const CARD_W = 560;
const CARD_H = 370;

const COLOR = {
  CARD_FRONT_BG:    0x1a150d,
  CARD_BACK_BG:     0x0e0b07,
  BORDER_FRONT:     0xc9a84c,
  BORDER_BACK:      0x8b6914,
  LABEL_FRONT:      0xb8a07a,
  LABEL_BACK:       0x8b6914,
  TEXT_MAIN:        0xe8d5a3,
  CORRECT:          0x4caf7d,
  WRONG:            0xc0392b,
  ORNAMENT:         0xc9a84c,
};

/* ═══════════════════════════════════════════════════════════════
   3. PHASER СЦЕНА — КАРТОЧКА
   ═══════════════════════════════════════════════════════════════ */
class CardScene extends Phaser.Scene {
  constructor() {
    super({ key: 'CardScene' });
    this.isShowingBack  = false;
    this.isBusy         = false;   // заблокирован ли переворот во время анимации
    this.currentData    = null;
    this.frontContainer = null;
    this.backContainer  = null;
    this.glowGfx        = null;
    this.cardRoot       = null;    // корневой контейнер (масштабируется при флипе)
  }

  /* ── preload ─────────────────────────────────────────────── */
  preload() {
    // Текстуры создаются программно в create(); внешние ресурсы
    // загружаются динамически через loadImageToFace().
  }

  /* ── create ──────────────────────────────────────────────── */
  create() {
    const cx = this.scale.width  / 2;
    const cy = this.scale.height / 2;

    /* --- Glow-графика (за карточкой) --- */
    this.glowGfx = this.add.graphics().setDepth(0);

    /* --- Корневой контейнер карточки (анимируется при флипе) --- */
    this.cardRoot = this.add.container(cx, cy).setDepth(1);

    /* --- Лицевая сторона --- */
    this.frontContainer = this._buildFace(
      COLOR.CARD_FRONT_BG,
      COLOR.BORDER_FRONT,
      COLOR.LABEL_FRONT,
      'Вопрос'
    );

    /* --- Тыльная сторона (скрыта при старте) --- */
    this.backContainer = this._buildFace(
      COLOR.CARD_BACK_BG,
      COLOR.BORDER_BACK,
      COLOR.LABEL_BACK,
      'Ответ'
    );
    this.backContainer.setVisible(false);

    this.cardRoot.add([this.frontContainer, this.backContainer]);

    /* --- Подписываемся на события от DOM-логики --- */
    EventBus.on('loadCardData',  this._handleLoad,      this);
    EventBus.on('flipCard',      this._animFlip,        this);
    EventBus.on('showBack',      this._showBackInstant, this);
    EventBus.on('setGlow',       this._setGlow,         this);
    EventBus.on('clearGlow',     this._clearGlow,       this);
  }

  /* ── _buildFace ──────────────────────────────────────────── */
  /**
   * Строит контейнер одной стороны карточки.
   * Структура:
   *   container
   *     ├─ bg         (Rectangle — фон)
   *     ├─ border     (Graphics — внешняя + внутренняя рамка)
   *     ├─ ornaments  (4 × Text «✦» по углам)
   *     ├─ labelText  (Text — «Вопрос» / «Ответ» вверху)
   *     └─ contentText (Text — основное содержимое)
   *   (imgObj добавляется динамически при type='image')
   */
  _buildFace(bgColor, borderColor, labelColor, labelStr) {
    const face = this.add.container(0, 0);

    /* Фон */
    const bg = this.add.rectangle(0, 0, CARD_W, CARD_H, bgColor, 1);
    face._bg = bg;

    /* Рамка */
    const brd = this.add.graphics();
    this._drawBorder(brd, borderColor);
    face._border = brd;

    /* Угловые орнаменты */
    const hw = CARD_W / 2 - 18;
    const hh = CARD_H / 2 - 18;
    const corners = [[-hw,-hh],[hw,-hh],[-hw,hh],[hw,hh]].map(([x,y]) =>
      this.add.text(x, y, '✦', {
        fontFamily: 'EB Garamond, serif',
        fontSize: '16px',
        color: this._intToHexStr(COLOR.ORNAMENT),
      }).setOrigin(0.5).setAlpha(0.45)
    );

    /* Метка стороны */
    const labelText = this.add.text(0, -CARD_H / 2 + 22, labelStr, {
      fontFamily: 'Cinzel Decorative, serif',
      fontSize: '11px',
      color: this._intToHexStr(labelColor),
      letterSpacing: 4,
    }).setOrigin(0.5).setAlpha(0.65);

    /* Основной текст контента */
    const contentText = this.add.text(0, 10, '', {
      fontFamily: 'EB Garamond, serif',
      fontSize: '24px',
      color: this._intToHexStr(COLOR.TEXT_MAIN),
      align: 'center',
      wordWrap: { width: CARD_W - 80 },
      lineSpacing: 6,
    }).setOrigin(0.5);

    face._contentText = contentText;
    face._imgObj      = null;

    face.add([bg, brd, ...corners, labelText, contentText]);
    return face;
  }

  /* ── _drawBorder ─────────────────────────────────────────── */
  _drawBorder(gfx, color) {
    const hw = CARD_W / 2;
    const hh = CARD_H / 2;
    gfx.clear();
    // Внешняя рамка
    gfx.lineStyle(1.5, color, 0.85);
    gfx.strokeRect(-hw, -hh, CARD_W, CARD_H);
    // Внутренняя рамка (декоративная)
    gfx.lineStyle(1, color, 0.25);
    gfx.strokeRect(-hw + 9, -hh + 9, CARD_W - 18, CARD_H - 18);
  }

  /* ── _handleLoad ─────────────────────────────────────────── */
    _handleLoad(data) {
      this.currentData = data;
      this.isShowingBack = false;
      this.isBusy = false;

      // ❗ очистка старых изображений
      [this.frontContainer, this.backContainer].forEach(face => {
        if (face._imgObj) {
          face._imgObj.destroy();
          face._imgObj = null;
        }
      });

      this._setFaceContent(this.frontContainer, data.front);
      this._setFaceContent(this.backContainer, data.back);

      this.frontContainer.setVisible(true);
      this.backContainer.setVisible(false);

      this.cardRoot.setScale(1, 1);
      this._clearGlow();

      EventBus.emit('cardReady');
    }

  /* ── _setFaceContent ─────────────────────────────────────── */
  _setFaceContent(face, sideData) {
    /* Удаляем старое изображение, если было */
    if (face._imgObj) {
      face._imgObj.destroy();
      face._imgObj = null;
    }

    if (sideData.type === 'text') {
      face._contentText.setText(sideData.content).setVisible(true);
    } else {
      /* type === 'image' */
      face._contentText.setVisible(false);
      this._loadImageToFace(face, sideData.content);
    }
  }

  /* ── _loadImageToFace ────────────────────────────────────── */
    _loadImageToFace(face, url) {
      const key = 'ci_' + this._simpleHash(url);

      const applyImage = () => {
        if (face._imgObj) {
          face._imgObj.destroy();
          face._imgObj = null;
        }

        const img = this.add.image(0, 10, key);

        const maxW = CARD_W - 60;
        const maxH = CARD_H - 80;

        const scale = Math.min(
          maxW / img.width,
          maxH / img.height,
          1
        );

        img.setOrigin(0.5);
        img.setScale(scale);

        face._imgObj = img;
        face.add(img);
      };

      // если уже загружено
      if (this.textures.exists(key)) {
        applyImage();
        return;
      }

      // если уже грузится — не дублируем
      if (this.load.isLoading()) {
        this.load.once(`filecomplete-image-${key}`, applyImage);
        return;
      }

      // грузим изображение
      this.load.image(key, url);

      this.load.once(`filecomplete-image-${key}`, applyImage);

      this.load.start();

    if (this.textures.exists(key)) {
      applyImage();
    } else {
      this.load.image(key, url);
      this.load.once('complete', applyImage);
      this.load.start();
    }
  }

  /* ── _animFlip ───────────────────────────────────────────── */
  /**
   * Анимация переворота:
   *   1. Сжимаем cardRoot по оси X → 0 (200 мс)
   *   2. На середине переключаем видимость сторон
   *   3. Разворачиваем обратно → 1 (200 мс)
   */
  _animFlip() {
    if (this.isBusy) return;
    this.isBusy = true;

    const HALF_DUR = 200;

    this.tweens.add({
      targets:  this.cardRoot,
      scaleX:   0,
      duration: HALF_DUR,
      ease:     'Cubic.easeIn',
      onComplete: () => {
        /* Переключаем стороны */
        this.isShowingBack = !this.isShowingBack;
        this.frontContainer.setVisible(!this.isShowingBack);
        this.backContainer.setVisible(this.isShowingBack);

        /* Раскрываем карточку */
        this.tweens.add({
          targets:  this.cardRoot,
          scaleX:   1,
          duration: HALF_DUR,
          ease:     'Cubic.easeOut',
          onComplete: () => {
            this.isBusy = false;
            EventBus.emit('flipComplete', this.isShowingBack);
          },
        });
      },
    });
  }

  /* ── _showBackInstant ────────────────────────────────────── */
  /** Мгновенный переворот (без анимации) — для восстановления состояния */
  _showBackInstant() {
    this.isShowingBack = true;
    this.frontContainer.setVisible(false);
    this.backContainer.setVisible(true);
  }

  /* ── _setGlow ────────────────────────────────────────────── */
  _setGlow(type) {
    const cx = this.scale.width  / 2;
    const cy = this.scale.height / 2;
    const color = type === 'correct' ? COLOR.CORRECT : COLOR.WRONG;

    this.glowGfx.clear();

    /* Несколько концентрических прямоугольников с убывающей прозрачностью */
    [12, 7, 3].forEach((pad, i) => {
      this.glowGfx.lineStyle(pad, color, 0.06 + i * 0.04);
      this.glowGfx.strokeRect(
        cx - CARD_W / 2 - pad,
        cy - CARD_H / 2 - pad,
        CARD_W + pad * 2,
        CARD_H + pad * 2
      );
    });

    /* Основная граница */
    this.glowGfx.lineStyle(2, color, 0.95);
    this.glowGfx.strokeRect(cx - CARD_W / 2, cy - CARD_H / 2, CARD_W, CARD_H);
  }

  /* ── _clearGlow ──────────────────────────────────────────── */
  _clearGlow() {
    this.glowGfx.clear();
  }

  /* ── Утилиты ─────────────────────────────────────────────── */
  _intToHexStr(int) {
    return '#' + int.toString(16).padStart(6, '0');
  }

  _simpleHash(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
      h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
    }
    return (h >>> 0).toString(36);
  }
}


/* ═══════════════════════════════════════════════════════════════
   4. ИНИЦИАЛИЗАЦИЯ PHASER
   ═══════════════════════════════════════════════════════════════ */
const game = new Phaser.Game({
  type:        Phaser.AUTO,
  width:       CARD_W + 40,
  height:      CARD_H + 40,
  transparent: true,
  parent:      'phaser-card',
  scene:       [CardScene],
  render:      { antialias: true, pixelArt: false },
});


/* ═══════════════════════════════════════════════════════════════
   5. DOM-ЛОГИКА И ИГРОВОЕ СОСТОЯНИЕ
   ═══════════════════════════════════════════════════════════════ */

/* ── Чтение данных Jinja2 из атрибутов <body> ── */
const $body         = document.body;
let CARD_INDICES
try {
  CARD_INDICES = JSON.parse($body.dataset.indices)
} catch (e) {
  console.error("JSON parse error:", e)
}
//const CARD_INDICES  = JSON.parse($body.dataset.indices);   // list[int]
const TOTAL_Q       = parseInt($body.dataset.total, 10);   // int
// SESSION_ID доступен через $body.dataset.session при необходимости

/* ── DOM-элементы ── */
const el = {
  countCorrect:  document.getElementById('count-correct'),
  countWrong:    document.getElementById('count-wrong'),
  countTotal:    document.getElementById('count-total'),
  cardPosCurrent:document.getElementById('card-pos-current'),
  cardPosTotal:  document.getElementById('card-pos-total'),
  answerInput:   document.getElementById('answer-input'),
  submitBtn:     document.getElementById('submit-btn'),
  flipBtn:       document.getElementById('flip-btn'),
  prevBtn:       document.getElementById('prev-btn'),
  nextBtn:       document.getElementById('next-btn'),
  footerDots:    document.getElementById('footer-dots'),
  cardHint:      document.getElementById('card-hint'),
  phaserCard:    document.getElementById('phaser-card'),
};

/* ── Игровое состояние ── */
const state = {
  step:        0,                              // текущий индекс в CARD_INDICES
  cardData:    null,                           // объект текущей карточки с сервера
  userAnswers: new Array(CARD_INDICES.length).fill(null),
  // userAnswers[i] = { answer: string, correct: boolean } | null
  stats: { correct: 0, wrong: 0 },
  isAnswered:  false,  // ответил ли пользователь на текущую карточку
  canFlip:     false,  // можно ли вручную переворачивать
  isLoading:   false,
};

/* ─────────────────────────────────────────────────────────────
   Инициализация UI
   ───────────────────────────────────────────────────────────── */
function initUI() {
  el.countTotal.textContent   = TOTAL_Q;
  el.cardPosTotal.textContent = TOTAL_Q;

  /* Генерируем точки-индикаторы в футере */
  el.footerDots.innerHTML = '';
  const maxDots = Math.min(CARD_INDICES.length, 40); // не больше 40 точек
  for (let i = 0; i < maxDots; i++) {
    const dot = document.createElement('span');
    dot.className = 'dot';
    dot.dataset.idx = i;
    el.footerDots.appendChild(dot);
  }
}

/* ─────────────────────────────────────────────────────────────
   Обновление точек-индикаторов
   ───────────────────────────────────────────────────────────── */
function updateDots() {
  const dots = el.footerDots.querySelectorAll('.dot');
  dots.forEach((dot, i) => {
    dot.className = 'dot';
    const ans = state.userAnswers[i];
    if (i === state.step)        dot.classList.add('dot--current');
    else if (ans?.correct)       dot.classList.add('dot--correct');
    else if (ans && !ans.correct) dot.classList.add('dot--wrong');
  });
}

/* ─────────────────────────────────────────────────────────────
   Обновление счётчиков прогресса
   ───────────────────────────────────────────────────────────── */
function updateStats() {
  el.countCorrect.textContent = state.stats.correct;
  el.countWrong.textContent   = state.stats.wrong;
}

/* ─────────────────────────────────────────────────────────────
   Получение карточки с сервера
   ───────────────────────────────────────────────────────────── */
async function fetchCard(id) {
  const resp = await fetch(`/card?id=${id}`);
  if (!resp.ok) throw new Error(`Ошибка загрузки карточки ${id}: ${resp.status}`);
  return resp.json();
}

/* ─────────────────────────────────────────────────────────────
   Нормализация ответа для сравнения
   ───────────────────────────────────────────────────────────── */
function normalizeAnswer(str) {
  return str
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ')
    // убираем знаки препинания по краям
    .replace(/^[.,!?;:—-]+|[.,!?;:—-]+$/g, '');
}

/* ─────────────────────────────────────────────────────────────
   Загрузка и отображение карточки
   ───────────────────────────────────────────────────────────── */
async function loadAndDisplayCard(step) {
  if (state.isLoading) return;
  state.isLoading = true;
  state.step = step;

  /* Показываем лоадер */
  el.cardHint.classList.remove('hidden');

  /* Обновляем UI */
  el.cardPosCurrent.textContent = step + 1;
  el.prevBtn.disabled = step === 0;
  el.nextBtn.disabled = step === CARD_INDICES.length - 1;
  updateDots();

  /* Убираем предыдущий glow с обёртки */
  el.phaserCard.classList.remove('glow-correct', 'glow-wrong');

  try {
    state.cardData = await fetchCard(CARD_INDICES[step]);
  } catch (err) {
    el.cardHint.textContent = '⚠ Не удалось загрузить карточку';
    state.isLoading = false;
    return;
  }

  /* Передаём данные в Phaser */
  EventBus.emit('loadCardData', state.cardData);
  // CardScene сообщит 'cardReady' когда отрендерит
}

/* ─────────────────────────────────────────────────────────────
   Восстановление состояния уже отвеченной карточки
   ───────────────────────────────────────────────────────────── */
function restoreAnsweredState(savedAnswer) {
  state.isAnswered = true;
  state.canFlip    = true;

  el.answerInput.value    = savedAnswer.answer;
  el.answerInput.disabled = true;
  el.submitBtn.disabled   = true;
  el.flipBtn.style.display = 'inline-flex';

  /* Небольшая задержка, чтобы Phaser успел отрисовать карточку */
  setTimeout(() => {
    EventBus.emit('showBack');
    EventBus.emit('setGlow', savedAnswer.correct ? 'correct' : 'incorrect');
    applyGlowClass(savedAnswer.correct);
  }, 80);
}

/* ─────────────────────────────────────────────────────────────
   Состояние свежей (не отвеченной) карточки
   ───────────────────────────────────────────────────────────── */
function setFreshCardState() {
  state.isAnswered = false;
  state.canFlip    = false;

  el.answerInput.value    = '';
  el.answerInput.disabled = false;
  el.submitBtn.disabled   = false;
  el.flipBtn.style.display = 'none';

  el.phaserCard.classList.remove('glow-correct', 'glow-wrong');
  EventBus.emit('clearGlow');

  /* Фокус на поле ввода (для удобства) */
  setTimeout(() => el.answerInput.focus(), 50);
}

/* ─────────────────────────────────────────────────────────────
   Применение CSS-класса glow к обёртке canvas
   ───────────────────────────────────────────────────────────── */
function applyGlowClass(correct) {
  el.phaserCard.classList.remove('glow-correct', 'glow-wrong');
  el.phaserCard.classList.add(correct ? 'glow-correct' : 'glow-wrong');
}

/* ─────────────────────────────────────────────────────────────
   Обработка события 'cardReady' от Phaser
   ───────────────────────────────────────────────────────────── */
EventBus.on('cardReady', () => {
  el.cardHint.classList.add('hidden');
  state.isLoading = false;

  const savedAnswer = state.userAnswers[state.step];
  if (savedAnswer !== null) {
    restoreAnsweredState(savedAnswer);
  } else {
    setFreshCardState();
  }
});

/* ─────────────────────────────────────────────────────────────
   Проверка ответа
   ───────────────────────────────────────────────────────────── */
function submitAnswer() {
  if (state.isAnswered || !state.cardData || state.isLoading) return;

  const userRaw    = el.answerInput.value;
  const userAnswer = normalizeAnswer(userRaw);
  if (!userAnswer) return;

  const correct = userAnswer === normalizeAnswer(state.cardData.back.answer_text);

  /* Сохраняем ответ в память */
  state.userAnswers[state.step] = { answer: userRaw, correct };

  /* Обновляем статистику (только для новых ответов) */
  if (correct) state.stats.correct++;
  else         state.stats.wrong++;
  updateStats();
  updateDots();

  /* Переводим UI в «отвечено» */
  state.isAnswered = true;
  state.canFlip    = true;
  el.answerInput.disabled = true;
  el.submitBtn.disabled   = true;
  el.flipBtn.style.display = 'inline-flex';

  /* Анимация переворота → тыльная сторона */
  EventBus.emit('flipCard');

  /* После завершения переворота ставим glow */
  EventBus.once('flipComplete', () => {
    EventBus.emit('setGlow', correct ? 'correct' : 'incorrect');
    applyGlowClass(correct);
  });
}

/* ─────────────────────────────────────────────────────────────
   Переворот по кнопке (только после ответа)
   ───────────────────────────────────────────────────────────── */
function handleFlipBtn() {
  if (!state.canFlip) return;
  EventBus.emit('flipCard');
}

/* ─────────────────────────────────────────────────────────────
   Навигация
   ───────────────────────────────────────────────────────────── */
function goNext() {
  if (state.step < CARD_INDICES.length - 1 && !state.isLoading) {
    loadAndDisplayCard(state.step + 1);
  }
}

function goPrev() {
  if (state.step > 0 && !state.isLoading) {
    loadAndDisplayCard(state.step - 1);
  }
}

/* ─────────────────────────────────────────────────────────────
   Привязка событий DOM
   ───────────────────────────────────────────────────────────── */
el.submitBtn.addEventListener('click', submitAnswer);
el.flipBtn.addEventListener('click', handleFlipBtn);
el.nextBtn.addEventListener('click', goNext);
el.prevBtn.addEventListener('click', goPrev);

el.answerInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') submitAnswer();
});

/* Клавиатурные быстрые клавиши */
document.addEventListener('keydown', (e) => {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
  if (e.key === 'ArrowRight') goNext();
  if (e.key === 'ArrowLeft')  goPrev();
  if (e.key === ' ' || e.key === 'f') handleFlipBtn();
});

/* ─────────────────────────────────────────────────────────────
   Запуск
   ───────────────────────────────────────────────────────────── */
/* Ждём, пока Phaser создаст сцену, затем грузим первую карточку */
document.addEventListener('DOMContentLoaded', () => {
  initUI();
  loadAndDisplayCard(0);
});
