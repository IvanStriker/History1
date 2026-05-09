"""add Training and TrainingCard tables

Revision ID: a7c4f2e1b839
Revises: 53bfa628d824
Create Date: 2026-05-09 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7c4f2e1b839"
down_revision = "53bfa628d824"
branch_labels = None
depends_on = None


def upgrade():
    # ─────────────────────────────────────────────────────
    # trainings
    # ─────────────────────────────────────────────────────

    op.create_table(
        "trainings",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True
        ),

        sa.Column(
            "score",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "cards_amount",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL"
        ),
    )

    # ─────────────────────────────────────────────────────
    # training_cards
    # ─────────────────────────────────────────────────────

    op.create_table(
        "training_cards",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False
        ),

        sa.Column(
            "training_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "card_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "user_answer",
            sa.Text(),
            nullable=True
        ),

        sa.Column(
            "is_valid_answer",
            sa.Boolean(),
            nullable=False
        ),

        sa.ForeignKeyConstraint(
            ["training_id"],
            ["trainings.id"],
            ondelete="CASCADE"
        ),

        sa.ForeignKeyConstraint(
            ["card_id"],
            ["cards.id"],
            ondelete="CASCADE"
        ),
    )


def downgrade():
    op.drop_table("training_cards")
    op.drop_table("trainings")