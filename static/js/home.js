/**
 * home.js — Phaser 3 фоновая сцена для страницы /home
 *
 * Создаёт атмосферный фон: медленно плавающие золотые частицы,
 * похожие на искры в старом архиве. Phaser-канвас прозрачен —
 * CSS-фон (тёмный) виден сквозь него.
 */

/* ─── Константы ──────────────────────────────────────────── */
const GOLD   = 0xc9a84c;
const GOLD2  = 0x8b6914;
const WHITE  = 0xf2e4c4;

/* ─── Вспомогательные утилиты ────────────────────────────── */
const rnd  = (min, max) => Math.random() * (max - min) + min;
const rndI = (min, max) => Math.floor(rnd(min, max));

/* ═══════════════════════════════════════════════════════════
   СЦЕНА: BackgroundScene
   ═══════════════════════════════════════════════════════════ */
class BackgroundScene extends Phaser.Scene {
  constructor() {
    super({ key: 'BackgroundScene' });
    this.orbs    = [];   // медленно дрейфующие частицы
    this.sparks  = [];   // короткоживущие искры
    this.lines   = [];   // слабые горизонтальные штрихи
    this.elapsed = 0;
  }

  /* ── create ───────────────────────────────────────────── */
  create() {
    const W = this.scale.width;
    const H = this.scale.height;

    /* --- Строим текстуры программно --- */
    this._makeOrbTexture('orb-lg', 10, GOLD, 0.7);
    this._makeOrbTexture('orb-sm', 4,  GOLD2, 0.5);
    this._makeOrbTexture('spark',  2,  WHITE, 0.9);

    /* --- Фоновый «виньетка»-градиент --- */
    const vignette = this.add.graphics();
    vignette.fillGradientStyle(0x000000, 0x000000, 0x000000, 0x000000, 0, 0, 0.7, 0.7);
    vignette.fillRect(0, 0, W, H);
    vignette.setAlpha(0.5);
    vignette.setDepth(10);

    /* --- Создаём «плавающие шары» --- */
    for (let i = 0; i < 28; i++) {
      this._spawnOrb(W, H, true);
    }

    /* --- Горизонтальные декоративные штрихи --- */
    this._drawLines(W, H);

    /* --- Статичная система частиц (Phaser 3.60 API) --- */
    this.add.particles(0, 0, 'spark', {
      x:        { min: 0, max: W },
      y:        { min: 0, max: H },
      speedX:   { min: -8, max: 8 },
      speedY:   { min: -18, max: -4 },
      alpha:    { start: 0.55, end: 0 },
      scale:    { start: 1, end: 0.3 },
      lifespan: { min: 3000, max: 7000 },
      frequency: 220,
      quantity:  1,
      depth:    2,
    });
  }

  /* ── update ───────────────────────────────────────────── */
  update(time, delta) {
    const W = this.scale.width;
    const H = this.scale.height;
    this.elapsed += delta;

    /* Двигаем шары */
    for (const orb of this.orbs) {
      orb.img.x += orb.vx;
      orb.img.y += orb.vy;

      /* Плавное мерцание */
      orb.img.alpha = orb.baseAlpha + Math.sin(time * 0.001 * orb.pulseFq + orb.phase) * 0.12;

      /* Перезапуск шара, вышедшего за экран */
      if (
        orb.img.x < -20 || orb.img.x > W + 20 ||
        orb.img.y < -20 || orb.img.y > H + 20
      ) {
        this._resetOrb(orb, W, H);
      }
    }
  }

  /* ── Вспомогательные методы ───────────────────────────── */

  /** Генерирует круглую текстуру с soft-glow */
  _makeOrbTexture(key, r, color, alpha) {
    const gfx = this.make.graphics({ x: 0, y: 0, add: false });
    const size = r * 4;

    // Внешнее свечение (несколько кругов с убывающей opacity)
    for (let i = 3; i >= 1; i--) {
      const a = (alpha * 0.25) / i;
      const hex = Phaser.Display.Color.IntegerToColor(color);
      gfx.fillStyle(color, a);
      gfx.fillCircle(size / 2, size / 2, r * (1 + i * 0.7));
    }

    // Ядро
    gfx.fillStyle(color, alpha);
    gfx.fillCircle(size / 2, size / 2, r);

    gfx.generateTexture(key, size, size);
    gfx.destroy();
  }

  /** Создаёт один «шар» и добавляет в массив */
  _spawnOrb(W, H, randomY = false) {
    const isLarge = Math.random() < 0.35;
    const tex     = isLarge ? 'orb-lg' : 'orb-sm';
    const img     = this.add.image(
      rnd(0, W),
      randomY ? rnd(0, H) : H + 20,
      tex
    ).setDepth(3);

    const orb = {
      img,
      vx:      rnd(-0.25, 0.25),
      vy:      rnd(-0.35, -0.08),
      baseAlpha: rnd(0.15, isLarge ? 0.6 : 0.4),
      pulseFq:   rnd(0.4, 1.4),
      phase:     rnd(0, Math.PI * 2),
    };
    img.setAlpha(orb.baseAlpha);
    this.orbs.push(orb);
  }

  /** Сбрасывает шар внизу экрана */
  _resetOrb(orb, W, H) {
    orb.img.x  = rnd(0, W);
    orb.img.y  = H + 20;
    orb.vx     = rnd(-0.25, 0.25);
    orb.vy     = rnd(-0.35, -0.08);
    orb.phase  = rnd(0, Math.PI * 2);
  }

  /** Рисует тонкие декоративные горизонтальные линии */
  _drawLines(W, H) {
    const gfx = this.add.graphics().setDepth(1).setAlpha(0.06);
    gfx.lineStyle(1, GOLD, 1);
    const count = 6;
    for (let i = 1; i <= count; i++) {
      const y = (H / (count + 1)) * i;
      gfx.beginPath();
      gfx.moveTo(0, y);
      gfx.lineTo(W, y);
      gfx.strokePath();
    }
  }
}

/* ═══════════════════════════════════════════════════════════
   ИНИЦИАЛИЗАЦИЯ PHASER
   ═══════════════════════════════════════════════════════════ */
window.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('phaser-bg');

  const config = {
    type: Phaser.AUTO,
    width:  window.innerWidth,
    height: window.innerHeight,
    backgroundColor: 'transparent',
    transparent: true,
    parent: 'phaser-bg',
    scene: [BackgroundScene],
    scale: {
      mode:          Phaser.Scale.RESIZE,
      autoCenter:    Phaser.Scale.CENTER_BOTH,
      width:         window.innerWidth,
      height:        window.innerHeight,
    },
    render: {
      antialias: true,
      pixelArt:  false,
    },
  };

  new Phaser.Game(config);
});