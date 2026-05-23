"""add app_settings table and admin tag/color to users

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- app_settings ---
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("app_name", sa.String(length=100), nullable=False, server_default="People Manager"),
        sa.Column("logo_path", sa.String(length=512), nullable=True),
        sa.Column("primary_color", sa.String(length=20), nullable=False, server_default="#6366f1"),
        sa.Column("secondary_color", sa.String(length=20), nullable=False, server_default="#3563e9"),
        sa.Column("welcome_text", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Insert default row so it always exists
    op.execute(
        "INSERT INTO app_settings (id, app_name, primary_color, secondary_color) "
        "VALUES (1, 'People Manager', '#6366f1', '#3563e9')"
    )

    # --- users: add admin_tag and admin_color ---
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("admin_tag", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("admin_color", sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("admin_color")
        batch_op.drop_column("admin_tag")

    op.drop_table("app_settings")
