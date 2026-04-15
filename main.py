"""
app.py — Flask-приложение «Хронос»

Стек:
  Flask + Flask-SQLAlchemy + Flask-Migrate (Alembic)

Переменные окружения:
  DATABASE_URL  — строка подключения к PostgreSQL
                  Пример: postgresql://user:pass@localhost:5432/chronos
"""

import os
import uuid
import csv
from random import sample

from flask import Flask, abort, jsonify, render_template, request
from flask_migrate import Migrate

from models import Card, db


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"]        = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"]      = {
        "pool_pre_ping": True,   # проверка живости соединения перед каждым запросом
        "pool_recycle":  1800,   # переоткрывать соединения каждые 30 минут
    }

    db.init_app(app)
    Migrate(app, db)             # регистрирует `flask db init/migrate/upgrade`

    # ── Маршруты ──────────────────────────────────────────────────────────────

    @app.route("/")
    @app.route("/home")
    def index():
        """
        Главная страница.

        Jinja2-параметры:
          site_title        — str       : название сайта
          site_subtitle     — str       : подзаголовок
          site_description  — str       : описание проекта
          total_cards_count — int       : число карточек в БД
          categories        — list[str] : уникальные категории (эпохи)
        """
        total      = db.session.query(Card).count()
        categories = [
            row[0]
            for row in (
                db.session.query(Card.category)
                .distinct()
                .order_by(Card.category)
                .all()
            )
        ]

        return render_template(
            "home.html",
            site_title="Хронос",
            site_subtitle="Карточки великих исторических деятелей",
            site_description=(
                "Тренируй знания истории с помощью интерактивных карточек. "
                "Античность, Средневековье, Новое время — выбирай эпоху "
                "и проверяй себя в удобном темпе."
            ),
            total_cards_count=total,
            categories=categories,
        )

    @app.route("/train")
    def train():
        """
        Страница тренировки.

        Jinja2-параметры:
          card_indices    — list[int] : случайный список id карточек
          total_questions — int       : количество вопросов
          session_id      — str       : UUID сессии
        """
        TRAIN_SIZE = 10

        all_ids: list[int] = [
            row[0]
            for row in db.session.query(Card.id).order_by(Card.id).all()
        ]
        selected = sample(all_ids, min(TRAIN_SIZE, len(all_ids))) if all_ids else []

        return render_template(
            "train.html",
            card_indices=selected,
            total_questions=len(selected),
            session_id=str(uuid.uuid4()),
        )

    @app.route("/card")
    def get_card():
        """
        REST-эндпоинт карточки.

        Query-параметры:
          id (int) — первичный ключ

        Ответ 200:
          { "id": int, "front": {...}, "back": {...} }
        Ошибки:
          400 — id не передан или не int
          404 — карточка не найдена
        """
        card_id = request.args.get("id", type=int)
        if card_id is None:
            abort(400, description="Параметр 'id' обязателен и должен быть целым числом.")

        card: Card | None = db.session.get(Card, card_id)
        if card is None:
            abort(404, description=f"Карточка с id={card_id} не найдена.")

        return jsonify(card.to_json())

    # ── Обработчики ошибок ────────────────────────────────────────────────────

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def handle_error(e):
        return jsonify(error=str(e.description)), e.code

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)