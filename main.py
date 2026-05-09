"""
app.py — Flask-приложение

Стек:
  Flask + Flask-SQLAlchemy + Flask-Migrate (Alembic)

Переменные окружения:
  DATABASE_URL  — строка подключения к PostgreSQL
                  Пример: postgresql://user:pass@localhost:5432/chronos
  SECRET_KEY    — секрет для Flask-сессий
"""

import os
import uuid
from random import sample

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_migrate import Migrate, upgrade as db_upgrade
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from models import Card, Category, User, db

_ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def _save_upload(file, side_label):
    """Save an uploaded image to static/images/. Returns (path, None) or (None, error_str)."""
    if not file or not file.filename:
        return None, f"Загрузите изображение для поля «{side_label}»."
    ext = os.path.splitext(secure_filename(file.filename))[1].lower().lstrip('.')
    if ext not in _ALLOWED_IMAGE_EXT:
        return None, f"Недопустимый формат файла для поля «{side_label}» (разрешены: png, jpg, gif, webp, svg)."
    images_dir = os.path.join('static', 'images')
    os.makedirs(images_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}.{ext}"
    file.save(os.path.join(images_dir, filename))
    return f"images/{filename}", None


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"]        = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"]      = {
        "pool_pre_ping": True,
        "pool_recycle":  1800,
    }
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    db.init_app(app)
    Migrate(app, db)

    with app.app_context():
        db_upgrade()

    # ── Контекстный процессор (доступен во всех шаблонах) ────────────────────

    @app.context_processor
    def inject_globals():
        user = None
        user_id = session.get("user_id")
        if user_id:
            user = db.session.get(User, user_id)
        return dict(current_user=user)

    # ── Маршруты ──────────────────────────────────────────────────────────────

    @app.route("/")
    @app.route("/home")
    def index():
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

    @app.route("/api/settings", methods=["POST"])
    def api_save_settings():
        if "user_id" not in session:
            return jsonify({"ok": False}), 401
        data = request.get_json(silent=True) or {}
        user = db.session.get(User, session["user_id"])
        if not user:
            return jsonify({"ok": False}), 404
        if "text_size"     in data: user.text_size     = float(data["text_size"])
        if "heading_scale" in data: user.heading_scale = float(data["heading_scale"])
        db.session.commit()
        return jsonify({"ok": True})

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
        card_id = request.args.get("id", type=int)
        if card_id is None:
            abort(400, description="Параметр 'id' обязателен и должен быть целым числом.")

        card: Card | None = db.session.get(Card, card_id)
        if card is None:
            abort(404, description=f"Карточка с id={card_id} не найдена.")

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
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not username or not password:
                flash("Введите имя пользователя и пароль.", "error")
                return render_template("sign_in.html")

            user: User | None = User.query.filter_by(username=username).first()
            if user is None or not check_password_hash(user.password, password):
                flash("Неверное имя пользователя или пароль.", "error")
                return render_template("sign_in.html")

            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("profile"))

        return render_template("sign_in.html")

    @app.route("/sign-up", methods=["GET", "POST"])
    def sign_up():
        if request.method == "POST":
            first_name       = request.form.get("first_name", "").strip()
            last_name        = request.form.get("last_name", "").strip()
            username         = request.form.get("username", "").strip()
            email            = request.form.get("email", "").strip()
            password         = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            bio              = request.form.get("bio", "").strip()

            if not all([first_name, last_name, username, email, password]):
                flash("Все обязательные поля должны быть заполнены.", "error")
                return render_template("sign_up.html")

            if len(password) < 8:
                flash("Пароль должен содержать не менее 8 символов.", "error")
                return render_template("sign_up.html")

            if password != confirm_password:
                flash("Пароли не совпадают.", "error")
                return render_template("sign_up.html")

            for u in User.query.filter_by(username=username).all():
                if check_password_hash(u.password, password):
                    flash("Пользователь с таким именем и паролем уже существует.", "error")
                    return render_template("sign_up.html")

            user = User(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                password=generate_password_hash(password),
                bio=bio or None,
            )
            db.session.add(user)
            db.session.commit()

            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("profile"))

        return render_template("sign_up.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/profile")
    def profile():
        return render_template("profile.html")

    @app.route("/new_card", methods=["GET", "POST"])
    def new_card():
        if "user_id" not in session:
            return redirect(url_for("sign_in"))
        if request.method == "POST":
            category    = request.form.get("category", "").strip()
            front_type  = request.form.get("front_type", "text")
            back_type   = request.form.get("back_type", "text")
            answer_text = request.form.get("answer_text", "").strip()

            if front_type == "image":
                front_content, err = _save_upload(request.files.get("front_file"), "лицевая сторона")
                if err:
                    flash(err, "error")
                    return redirect(url_for("new_card"))
            else:
                front_content = request.form.get("front_content", "").strip()

            if back_type == "image":
                back_content, err = _save_upload(request.files.get("back_file"), "оборотная сторона")
                if err:
                    flash(err, "error")
                    return redirect(url_for("new_card"))
            else:
                back_content = request.form.get("back_content", "").strip()

            errors = []
            if not category:    errors.append("Укажите категорию.")
            if not answer_text: errors.append("Укажите краткий ответ.")
            if front_type == "text" and not front_content:
                errors.append("Введите текст лицевой стороны.")
            if back_type == "text" and not back_content:
                errors.append("Введите текст оборотной стороны.")
            if errors:
                flash(" ".join(errors), "error")
                return redirect(url_for("new_card"))

            card = Card(
                category=category, front_type=front_type, front_content=front_content,
                back_type=back_type, back_content=back_content, answer_text=answer_text,
                user_id=session["user_id"],
            )
            db.session.add(card)
            db.session.commit()
            return redirect(url_for("cards_page"))

        existing_categories = [
            row[0] for row in db.session.query(Card.category).distinct().order_by(Card.category).all()
        ]
        return render_template("new_card.html", existing_categories=existing_categories)

    @app.route("/new_category", methods=["GET", "POST"])
    def new_category():
        if "user_id" not in session:
            return redirect(url_for("sign_in"))
        if request.method == "POST":
            name        = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            if not all([name, description]):
                flash("Все поля обязательны.", "error")
                return redirect(url_for("new_category"))
            cat = Category(name=name, description=description, creator_id=session["user_id"])
            db.session.add(cat)
            db.session.commit()
            return redirect(url_for("categories"))
        return render_template("new_category.html")

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
