"""add backups table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("destination_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "full_path",
            sa.String(length=1024),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "size_bytes",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "type",
            sa.String(length=20),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ok",
        ),
        sa.Column(
            "notes",
            sa.String(length=512),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backups_id", "backups", ["id"])


def downgrade() -> None:
    op.drop_index("ix_backups_id", table_name="backups")
    op.drop_table("backups")
