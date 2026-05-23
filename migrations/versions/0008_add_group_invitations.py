"""add group invitation fields and user invitation_id

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- invitations: add group invitation fields ---
    with op.batch_alter_table("invitations") as batch_op:
        batch_op.add_column(
            sa.Column("type", sa.String(length=20), nullable=False, server_default="personal")
        )
        batch_op.add_column(
            sa.Column("max_uses", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("current_uses", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("label", sa.String(length=150), nullable=True)
        )

    # --- users: add invitation_id FK ---
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("invitation_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_users_invitation_id",
            "invitations",
            ["invitation_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_invitation_id", type_="foreignkey")
        batch_op.drop_column("invitation_id")

    with op.batch_alter_table("invitations") as batch_op:
        batch_op.drop_column("label")
        batch_op.drop_column("current_uses")
        batch_op.drop_column("max_uses")
        batch_op.drop_column("type")
