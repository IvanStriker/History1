"""
models.py — SQLAlchemy-модели
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Card(db.Model):
    __tablename__ = "cards"

    id            = db.Column(db.Integer,     primary_key=True)
    category      = db.Column(db.Text,        nullable=False)
    front_type    = db.Column(db.Text,        nullable=False, default="text")
    front_content = db.Column(db.Text,        nullable=False)
    back_type     = db.Column(db.Text,        nullable=False, default="text")
    back_content  = db.Column(db.Text,        nullable=False)
    answer_text   = db.Column(db.Text,        nullable=False)

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