"""
app.py — Flask-приложение

Стек:
  Flask + Flask-SQLAlchemy + Flask-Migrate (Alembic)

Переменные окружения:
  DATABASE_URL  — строка подключения к PostgreSQL
                  Пример: postgresql://user:pass@localhost:5432/chronos
  SECRET_KEY    — секрет для Flask-сессий
"""

import json
import logging
import os
import urllib.request
import urllib.error
import uuid
from random import sample

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_migrate import Migrate, upgrade as db_upgrade
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from models import Card, Category, CategoryCard, User, Training, TrainingCard, db

logger = logging.getLogger(__name__)


def _call_rag(path: str, data: dict, timeout: int = 10) -> dict | None:
    """Отправляет POST-запрос к RAG-сервису. Возвращает None при любой ошибке."""
    rag_url = os.environ.get("RAG_URL", "")
    if not rag_url:
        return None
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{rag_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.warning(f"RAG call {path} failed: {e}")
        return None


def _card_rag_dict(card: Card) -> dict:
    return {
        "id": card.id,
        "front_type": card.front_type,
        "front_content": card.front_content if card.front_type == "text" else "",
        "back_type": card.back_type,
        "back_content": card.back_content if card.back_type == "text" else "",
        "answer_text": card.answer_text or "",
    }


def _call_rag_bg(path: str, data: dict, timeout: int = 60) -> None:
    """Fire-and-forget: отправляет RAG-запрос в фоновом треде."""
    import threading
    threading.Thread(target=_call_rag, args=(path, data, timeout), daemon=True).start()


def _bootstrap_rag(app: Flask) -> None:
    """При старте: если RAG пуст — загружает все карточки и подборки."""
    rag_url = os.environ.get("RAG_URL", "")
    if not rag_url:
        return
    try:
        req = urllib.request.Request(f"{rag_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            health = json.loads(resp.read())
        if health.get("stores", {}).get("all_cards", 0) > 0:
            return
    except Exception:
        return

    with app.app_context():
        cards = db.session.query(Card).all()
        all_dicts = [_card_rag_dict(c) for c in cards]
        if all_dicts:
            _call_rag("/build", {"scope": "all_cards", "cards": all_dicts}, timeout=120)
            logger.info(f"RAG bootstrapped all_cards: {len(all_dicts)} cards")

        categories = db.session.query(Category).all()
        for cat in categories:
            cat_cards = [_card_rag_dict(cc.card) for cc in cat.card_entries.all()]
            if cat_cards:
                _call_rag("/build", {"scope": f"category_{cat.id}", "cards": cat_cards}, timeout=60)
                logger.info(f"RAG bootstrapped category_{cat.id}: {len(cat_cards)} cards")

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

    import threading
    threading.Thread(target=_bootstrap_rag, args=(app,), daemon=True).start()

    # ── Контекстный процессор (доступен во всех шаблонах) ────────────────────

    @app.context_processor
    def inject_globals():
        user = None
        user_id = session.get("user_id")
        if user_id:
            user = db.session.get(User, user_id)
        all_categories = db.session.query(Category).order_by(Category.name).all()
        return dict(current_user=user, all_categories=all_categories)

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
        all_cats = db.session.query(Category).order_by(Category.name).all()
        train_categories = [
            {"name": cat.name, "count": cat.card_entries.count()}
            for cat in all_cats
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
            train_categories=train_categories,
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
    
    @app.route("/history")
    def history():
        if "user_id" not in session:
            return redirect(url_for("sign_in"))

        user_id = session["user_id"]

        trainings = db.session.query(Training)\
            .filter_by(user_id=user_id)\
            .order_by(Training.id.desc())\
            .all()

        return render_template("history.html", trainings=trainings)
    
    @app.route("/history/<int:training_id>")
    def history_detail(training_id):
        if "user_id" not in session:
            return redirect(url_for("sign_in"))
        training = db.session.get(Training, training_id)
        if not training:
            abort(404, "Тренировка не найдена.")
        if training.user_id != session["user_id"]:
            abort(403, "Нет доступа.")
        detail_cards = []
        for tc in training.cards:
            card = tc.card
            front_content = card.front_content
            if card.front_type == "image":
                front_content = url_for("static", filename=front_content.replace("./", ""))
            detail_cards.append({
                "tc":            tc,
                "front_type":    card.front_type,
                "front_content": front_content,
                "answer_text":   card.answer_text,
            })
        return render_template("training_detail.html", training=training, detail_cards=detail_cards)

    @app.route("/train/complete", methods=["POST"])
    def train_complete():
        if "user_id" not in session:
            return jsonify({"ok": False, "error": "Unauthorized"}), 401

        data = request.get_json(silent=True) or {}
        card_results = data.get("results", [])  # список {card_id, user_answer, is_correct}

        if not card_results:
            return jsonify({"ok": False, "error": "No results"}), 400

        # Создаём запись тренировки
        training = Training(
            user_id=session["user_id"],
            score=sum(1 for r in card_results if r.get("is_correct")),
            cards_amount=len(card_results)
        )
        db.session.add(training)
        db.session.flush()  # чтобы получить training.id

        # Создаём записи для каждой карточки
        for res in card_results:
            tc = TrainingCard(
                training_id=training.id,
                card_id=res.get("card_id"),
                user_answer=res.get("user_answer"),
                is_valid_answer=bool(res.get("is_correct"))
            )
            db.session.add(tc)

        db.session.commit()

        return jsonify({"ok": True, "training_id": training.id})

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
                "user_id":       card.user_id
            })
        return render_template("cards.html", cards=cards_data)

    @app.route("/cards/edit", methods=["GET", "POST"])
    def cards_edit():
        if "user_id" not in session:
            return redirect(url_for("sign_in"))
        card_id = (request.args if request.method == "GET" else request.form).get("card_id", type=int)
        if not card_id:
            abort(400, "Не указан ID карточки.")
        card = db.session.get(Card, card_id)
        if not card:
            abort(404, "Карточка не найдена.")
        _u = db.session.get(User, session["user_id"])
        if card.user_id != session["user_id"] and not (_u and _u.is_admin):
            abort(403, "Нет доступа.")

        if request.method == "POST":
            category    = request.form.get("category", "").strip()
            front_type  = request.form.get("front_type", "text")
            back_type   = request.form.get("back_type", "text")
            answer_text = request.form.get("answer_text", "").strip()

            if front_type == "image":
                f = request.files.get("front_file")
                if f and f.filename:
                    front_content, err = _save_upload(f, "лицевая сторона")
                    if err:
                        flash(err, "error")
                        return redirect(url_for("cards_edit", card_id=card_id))
                else:
                    front_content = request.form.get("front_keep", "").strip()
                    if not front_content:
                        flash("Загрузите изображение для поля «лицевая сторона».", "error")
                        return redirect(url_for("cards_edit", card_id=card_id))
            else:
                front_content = request.form.get("front_content", "").strip()

            if back_type == "image":
                f = request.files.get("back_file")
                if f and f.filename:
                    back_content, err = _save_upload(f, "оборотная сторона")
                    if err:
                        flash(err, "error")
                        return redirect(url_for("cards_edit", card_id=card_id))
                else:
                    back_content = request.form.get("back_keep", "").strip()
                    if not back_content:
                        flash("Загрузите изображение для поля «оборотная сторона».", "error")
                        return redirect(url_for("cards_edit", card_id=card_id))
            else:
                back_content = request.form.get("back_content", "").strip()

            errors = []
            if not category:    errors.append("Укажите категорию.")
            if not answer_text: errors.append("Укажите краткий ответ.")
            if front_type == "text" and not front_content: errors.append("Введите текст лицевой стороны.")
            if back_type  == "text" and not back_content:  errors.append("Введите текст оборотной стороны.")
            if errors:
                flash(" ".join(errors), "error")
                return redirect(url_for("cards_edit", card_id=card_id))

            card.category      = category
            card.front_type    = front_type
            card.front_content = front_content
            card.back_type     = back_type
            card.back_content  = back_content
            card.answer_text   = answer_text
            db.session.commit()
            return redirect(url_for("cards_mine"))

        existing_categories = [
            row[0] for row in db.session.query(Card.category).distinct().order_by(Card.category).all()
        ]
        return render_template("edit_card.html", card=card, existing_categories=existing_categories)

    @app.route("/categories/edit", methods=["GET", "POST"])
    def categories_edit():
        if "user_id" not in session:
            return redirect(url_for("sign_in"))
        category_id = (request.args if request.method == "GET" else request.form).get("category_id", type=int)
        if not category_id:
            abort(400, "Не указан ID подборки.")
        cat = db.session.get(Category, category_id)
        if not cat:
            abort(404, "Подборка не найдена.")
        _u = db.session.get(User, session["user_id"])
        if cat.creator_id != session["user_id"] and not (_u and _u.is_admin):
            abort(403, "Нет доступа.")

        if request.method == "POST":
            name        = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            if not all([name, description]):
                flash("Все поля обязательны.", "error")
                return redirect(url_for("categories_edit", category_id=category_id))
            cat.name        = name
            cat.description = description
            db.session.query(CategoryCard).filter_by(category_id=cat.id).delete()
            card_ids = request.form.getlist("card_ids[]", type=int)
            cat_cards_for_rag = []
            for cid in card_ids:
                c = db.session.get(Card, cid)
                if c:
                    db.session.add(CategoryCard(card_id=cid, category_id=cat.id))
                    cat_cards_for_rag.append(_card_rag_dict(c))
            db.session.commit()
            if cat_cards_for_rag:
                _call_rag_bg("/build", {"scope": f"category_{cat.id}", "cards": cat_cards_for_rag})
            return redirect(url_for("categories_mine"))

        all_cards = db.session.query(Card).order_by(Card.id).all()
        current_card_ids = {ce.card_id for ce in cat.card_entries.all()}
        return render_template("edit_category.html", category=cat,
                               all_cards=all_cards, current_card_ids=current_card_ids)

    @app.route("/cards/delete", methods=["DELETE"])
    def cards_delete():
        if "user_id" not in session:
            return jsonify({"ok": False}), 401
        data = request.get_json(silent=True) or {}
        card = db.session.get(Card, data.get("id"))
        if not card:
            return jsonify({"ok": False}), 404
        _u = db.session.get(User, session["user_id"])
        if card.user_id != session["user_id"] and not (_u and _u.is_admin):
            return jsonify({"ok": False}), 403
        db.session.delete(card)
        db.session.commit()
        return jsonify({"ok": True})

    @app.route("/categories/delete", methods=["DELETE"])
    def categories_delete():
        if "user_id" not in session:
            return jsonify({"ok": False}), 401
        data = request.get_json(silent=True) or {}
        cat  = db.session.get(Category, data.get("id"))
        if not cat:
            return jsonify({"ok": False}), 404
        _u = db.session.get(User, session["user_id"])
        if cat.creator_id != session["user_id"] and not (_u and _u.is_admin):
            return jsonify({"ok": False}), 403
        db.session.delete(cat)
        db.session.commit()
        return jsonify({"ok": True})

    @app.route("/cards/mine")
    def cards_mine():
        if "user_id" not in session:
            return redirect(url_for("sign_in"))
        
        user_id = session["user_id"]
        user_cards = db.session.query(Card)\
            .filter_by(user_id=user_id)\
            .order_by(Card.id.desc())\
            .all()

        cards_data = []
        for card in user_cards:
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
                "category":      card.category,
                "user_id":       card.user_id
            })

        return render_template("cards.html", 
                             cards=cards_data, 
                             title="Мои карточки")

    @app.route("/categories/mine")
    def categories_mine():
        if "user_id" not in session:
            return redirect(url_for("sign_in"))
        
        user_id = session["user_id"]
        user_categories = db.session.query(Category)\
            .filter_by(creator_id=user_id)\
            .order_by(Category.id.desc())\
            .all()

        return render_template("categories.html", 
                             categories=user_categories, 
                             title="Мои подборки")

    @app.route("/train", methods=["GET", "POST"])
    def train():
        if request.method == "POST":
            category = request.form.get("category", "").strip()
            mode     = request.form.get("mode", "all")
            count    = request.form.get("count", type=int)

            if category == "Все карточки":
                all_ids = [row[0] for row in db.session.query(Card.id).order_by(Card.id).all()]
            else:
                cat = Category.query.filter_by(name=category).first()
                all_ids = [ce.card_id for ce in cat.card_entries.all()] if cat else []

            if mode == "random" and count and count > 0:
                selected = sample(all_ids, min(count, len(all_ids))) if all_ids else []
            else:
                selected = list(all_ids)

            return render_template(
                "train.html",
                card_indices=selected,
                total_questions=len(selected),
                session_id=str(uuid.uuid4()),
            )

        # GET — legacy: 10 random from all cards
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
        """Страница со всеми подборками (для всех пользователей)"""
        all_categories = db.session.query(Category)\
            .order_by(Category.id.desc())\
            .all()

        return render_template(
            "categories.html", 
            categories=all_categories, 
            title="Все подборки"
        )

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
            _call_rag_bg("/update_card", _card_rag_dict(card))
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
            db.session.flush()
            card_ids = request.form.getlist("card_ids[]", type=int)
            cat_cards_for_rag = []
            for cid in card_ids:
                c = db.session.get(Card, cid)
                if c:
                    db.session.add(CategoryCard(card_id=cid, category_id=cat.id))
                    cat_cards_for_rag.append(_card_rag_dict(c))
            db.session.commit()
            if cat_cards_for_rag:
                _call_rag_bg("/build", {"scope": f"category_{cat.id}", "cards": cat_cards_for_rag})
            return redirect(url_for("categories"))
        all_cards = db.session.query(Card).order_by(Card.id).all()
        return render_template("new_category.html", all_cards=all_cards, current_card_ids=set())

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        data     = request.get_json(silent=True) or {}
        messages = data.get("messages", [])
        rag_scope = data.get("rag_scope", "none")

        if not messages:
            return jsonify({"ok": False, "error": "No messages"}), 400
        valid_roles = {"user", "assistant"}
        for msg in messages:
            if msg.get("role") not in valid_roles or not isinstance(msg.get("content"), str):
                return jsonify({"ok": False, "error": "Invalid message format"}), 400

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return jsonify({"ok": False, "error": "Chat is not configured on this server."}), 503

        # ── RAG: получаем релевантные карточки ───────────────────────────────
        rag_context = ""
        if rag_scope != "none":
            last_user = next(
                (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
            )
            if last_user:
                rag_result = _call_rag(
                    "/search",
                    {"query": last_user, "scope": rag_scope, "k": 5},
                    timeout=10,
                )
                docs = (rag_result or {}).get("docs", [])
                if docs:
                    lines = ["\n\nРелевантные карточки из базы знаний:"]
                    for i, doc in enumerate(docs, 1):
                        front = doc.get("front_content", "").strip()
                        back  = doc.get("back_content", "").strip()
                        ans   = doc.get("answer_text", "").strip()
                        lines.append(f"\n[{i}] Вопрос: {front}")
                        if back:
                            lines.append(f"    Оборот: {back}")
                        if ans:
                            lines.append(f"    Ответ: {ans}")
                    lines.append("\nИспользуй эти карточки при ответе, если они релевантны.")
                    rag_context = "\n".join(lines)

        try:
            system_prompt = (
                "Ты — знающий помощник по советской истории. "
                "Помогай пользователю изучать исторических деятелей СССР: "
                "биографии, роль в истории, исторический контекст. "
                "Отвечай на русском языке, в тёплом академическом тоне."
                + rag_context
            )
            lc_messages = [SystemMessage(content=system_prompt)]
            for msg in messages:
                if msg["role"] == "user":
                    lc_messages.append(HumanMessage(content=msg["content"]))
                else:
                    lc_messages.append(AIMessage(content=msg["content"]))
            llm = ChatOpenAI(
                openai_api_base="https://api.mistral.ai/v1",
                model="mistral-large-latest",
                api_key=api_key,
            )
            response = llm.invoke(lc_messages)
            return jsonify({"ok": True, "reply": response.content})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 502

    @app.route("/api/profile/update", methods=["POST"])
    def api_profile_update():
        if "user_id" not in session:
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        user = db.session.get(User, session["user_id"])
        if not user:
            return jsonify({"ok": False, "error": "Not found"}), 404
        for field in ("first_name", "last_name", "username", "email"):
            val = data.get(field, "").strip()
            if val:
                setattr(user, field, val)
        user.bio = data.get("bio", "").strip() or None
        new_pw = data.get("new_password", "")
        if new_pw:
            if len(new_pw) < 8:
                return jsonify({"ok": False, "error": "Пароль должен содержать не менее 8 символов."}), 400
            if new_pw != data.get("confirm_password", ""):
                return jsonify({"ok": False, "error": "Пароли не совпадают."}), 400
            user.password = generate_password_hash(new_pw)
        db.session.commit()
        return jsonify({"ok": True})

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