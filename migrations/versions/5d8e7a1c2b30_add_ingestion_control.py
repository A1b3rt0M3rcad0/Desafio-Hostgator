"""add automatic ingestion control

Revision ID: 5d8e7a1c2b30
Revises: 8c1f2a6d9b40
Create Date: 2026-08-01 02:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5d8e7a1c2b30"
down_revision: Union[str, Sequence[str], None] = "8c1f2a6d9b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_control",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "cursor_position",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("source_version", sa.String(length=255), nullable=True),
        sa.Column(
            "worker_state",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'DISABLED'"),
        ),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO ingestion_control "
            "(id, enabled, cursor_position, worker_state) "
            "VALUES (1, 0, 0, 'DISABLED')"
        )
    )


def downgrade() -> None:
    op.drop_table("ingestion_control")
