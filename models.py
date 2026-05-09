"""
models.py — SQLAlchemy-модели
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ── Карточки ─────────────────────────────────────────────────────────────────

class Card(db.Model):
    __tablename__ = "cards"

    id            = db.Column(db.Integer,     primary_key=True)
    category      = db.Column(db.Text,        nullable=False)
    front_type    = db.Column(db.Text,        nullable=False, default="text")
    front_content = db.Column(db.Text,        nullable=False)
    back_type     = db.Column(db.Text,        nullable=False, default="text")
    back_content  = db.Column(db.Text,        nullable=False)
    answer_text   = db.Column(db.Text,        nullable=False)
    user_id       = db.Column(db.Integer,     db.ForeignKey("users.id"), nullable=True)

    creator = db.relationship("User", backref=db.backref("owned_cards", lazy="dynamic"))

    def front_dict(self) -> dict:
        return {"type": self.front_type, "content": self.front_content}

    def back_dict(self) -> dict:
        return {
            "type":        self.back_type,
            "content":     self.back_content,
            "answer_text": self.answer_text,
        }

    def to_json(self) -> dict:
        return {"id": self.id, "front": self.front_dict(), "back": self.back_dict()}

    def __repr__(self) -> str:
        return f"<Card id={self.id} category={self.category!r}>"


# ── Пользователи ─────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"

    id             = db.Column(db.Integer, primary_key=True)
    first_name     = db.Column(db.Text,    nullable=False)          # len > 0
    last_name      = db.Column(db.Text,    nullable=False)          # len > 0
    username       = db.Column(db.Text,    nullable=False)          # len > 0; пара (username+password) уникальна
    email          = db.Column(db.Text,    nullable=False)
    password       = db.Column(db.Text,    nullable=False)          # bcrypt-хэш
    bio            = db.Column(db.Text,    nullable=True)           # len >= 0
    text_size      = db.Column(db.Float,   nullable=True)           # px, напр. 16.0
    heading_scale  = db.Column(db.Float,   nullable=True)           # коэффициент, напр. 1.0

    categories = db.relationship("Category", back_populates="creator",
                                 lazy="dynamic", cascade="all, delete-orphan")

    trainings = db.relationship("Training", back_populates="user",
                                lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


# ── Тематические подборки ─────────────────────────────────────────────────────

class Category(db.Model):
    __tablename__ = "categories"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.Text,    nullable=False)   # len > 0
    description = db.Column(db.Text,    nullable=False)   # len > 0
    creator_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    creator      = db.relationship("User",         back_populates="categories")
    card_entries = db.relationship("CategoryCard", back_populates="category",
                                   lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"


# ── Связь подборка ↔ карточка ─────────────────────────────────────────────────

class CategoryCard(db.Model):
    __tablename__ = "category_cards"

    id          = db.Column(db.Integer, primary_key=True)
    card_id     = db.Column(db.Integer, db.ForeignKey("cards.id"),      nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    card     = db.relationship("Card",     foreign_keys=[card_id])
    category = db.relationship("Category", back_populates="card_entries",
                                foreign_keys=[category_id])

    def __repr__(self) -> str:
        return f"<CategoryCard card={self.card_id} cat={self.category_id}>"


class Training(db.Model):
    __tablename__ = "trainings"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    score = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    cards_amount = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    user = db.relationship(
        "User",
        back_populates="trainings"
    )

    cards = db.relationship(
        "TrainingCard",
        back_populates="training",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return f"<Training id={self.id} score={self.score}>"
    

class TrainingCard(db.Model):
    __tablename__ = "training_cards"

    id = db.Column(db.Integer, primary_key=True)

    training_id = db.Column(
        db.Integer,
        db.ForeignKey("trainings.id"),
        nullable=False
    )

    card_id = db.Column(
        db.Integer,
        db.ForeignKey("cards.id"),
        nullable=False
    )

    user_answer = db.Column(
        db.Text,
        nullable=True
    )

    is_valid_answer = db.Column(
        db.Boolean,
        nullable=False
    )

    training = db.relationship(
        "Training",
        back_populates="cards"
    )

    card = db.relationship("Card")

    def __repr__(self):
        return (
            f"<TrainingCard "
            f"training={self.training_id} "
            f"card={self.card_id}>"
        )