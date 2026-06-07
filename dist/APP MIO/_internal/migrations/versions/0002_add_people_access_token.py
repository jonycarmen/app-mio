"""add people access token

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-24 00:30:00.000000

"""
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("people", sa.Column("access_token", sa.String(length=36), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id FROM people")).fetchall()
    for row in rows:
        connection.execute(
            sa.text("UPDATE people SET access_token = :token WHERE id = :person_id"),
            {"token": str(uuid4()), "person_id": row.id},
        )
    op.create_index("ix_people_access_token", "people", ["access_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_people_access_token", table_name="people")
    op.drop_column("people", "access_token")