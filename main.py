"""
app.py — Flask-приложение

Стек:
  Flask + Flask-SQLAlchemy + Flask-Migrate (Alembic)

Переменные окружения:
  DATABASE_URL  — строка подключения к PostgreSQL
                  Пример: postgresql://user:pass@localhost:5432/chronos
"""

import os
import uuid
from random import sample
import base64

from flask import Flask, abort, jsonify, render_template, request, url_for
from flask_migrate import Migrate, upgrade as db_upgrade

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
    Migrate(app, db)

    with app.app_context():
        db_upgrade()

    # ── Контекстный процессор (доступен во всех шаблонах) ────────────────────

    @app.context_processor
    def inject_globals():
        """Передаёт current_user во все шаблоны. Пока заглушка — None."""
        return dict(current_user=None)

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
            site_title="Историческая игра",
            site_subtitle="Карточки великих исторических деятелей",
            site_description=(
                "Тренируй знания истории с помощью интерактивных карточек. "
                "Здесь мы сосредоточимся на деятелях СССР."
            ),
            total_cards_count=total,
            categories=categories,
        )

    @app.route("/settings")
    def settings():
        return render_template("settings.html")

    @app.route("/cards")
    def cards_page():
        all_cards = db.session.query(Card).order_by(Card.id).all()
        cards_data = []
        for card in all_cards:
            front_content = card.front_content
            if card.front_type == "image":
                front_content = url_for("static", filename=front_content.replace("./", ""))
            back_content = card.back_content
            if card.back_type == "image":
                back_content = url_for("static", filename=back_content.replace("./", ""))
            cards_data.append({
                "id":            card.id,
                "front_type":    card.front_type,
                "front_content": front_content,
                "back_type":     card.back_type,
                "back_content":  back_content,
                "answer_text":   card.answer_text,
            })
        return render_template("cards.html", cards=cards_data)

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
          id (int)

        Ответ:
          {
            "id": int,
            "front": { "type": "text|image", "content": str },
            "back": { ... }
          }
        """
        card_id = request.args.get("id", type=int)
        if card_id is None:
            abort(400, description="Параметр 'id' обязателен и должен быть целым числом.")

        card: Card | None = db.session.get(Card, card_id)
        if card is None:
            abort(404, description=f"Карточка с id={card_id} не найдена.")

        # ── FRONT ─────────────────────────────────────────────
        if getattr(card, "front_type", "text") == "image":
            image_path = card.front_content

            if not image_path or not os.path.exists('static/' + image_path):
                abort(500, description="Файл изображения не найден.")

            image_path = card.front_content.replace("./", "")
            front = {
                "type": "image",
                "content": f"{url_for('static', filename=image_path)}",
            }
        else:
            front = {
                "type": "text",
                "content": card.front_content,
            }

        # ── BACK (без изменений логики, можно аналогично расширить при необходимости) ──
        back = card.to_json().get("back") if hasattr(card, "to_json") else {}

        return jsonify({
            "id": card.id,
            "front": front,
            "back": back,
        })

    @app.route("/categories")
    def categories():
        return render_template("categories.html")

    @app.route("/sign-in", methods=["GET", "POST"])
    def sign_in():
        return render_template("sign_in.html")

    @app.route("/sign-up", methods=["GET", "POST"])
    def sign_up():
        return render_template("sign_up.html")

    @app.route("/profile")
    def profile():
        return render_template("profile.html")

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