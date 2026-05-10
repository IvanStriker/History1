"""add is_admin to users and created_at to trainings

Revision ID: c5f2a8b91e34
Revises: a7c4f2e1b839
Create Date: 2026-05-10 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c5f2a8b91e34"
down_revision = "a7c4f2e1b839"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "trainings",
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_column("users", "is_admin")
    op.drop_column("trainings", "created_at")
