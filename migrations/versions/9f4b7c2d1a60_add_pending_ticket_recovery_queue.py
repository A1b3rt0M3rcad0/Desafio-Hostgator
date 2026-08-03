"""add pending ticket recovery queue

Revision ID: 9f4b7c2d1a60
Revises: 5d8e7a1c2b30
Create Date: 2026-08-02 12:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9f4b7c2d1a60"
down_revision: Union[str, Sequence[str], None] = "5d8e7a1c2b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_pending_tickets",
        sa.Column("external_ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("requester_external_id", sa.BigInteger(), nullable=False),
        sa.Column("requester_email", sa.String(length=255), nullable=False),
        sa.Column("source_version", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("source_payload", sa.JSON(), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.UniqueConstraint(
            "external_ticket_id",
            name="uq_ingestion_pending_tickets_external_ticket_id",
        ),
    )
    op.create_index(
        op.f("ix_ingestion_pending_tickets_requester_email"),
        "ingestion_pending_tickets",
        ["requester_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ingestion_pending_tickets_requester_external_id"),
        "ingestion_pending_tickets",
        ["requester_external_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            "UPDATE ingestion_control "
            "SET cursor_position = 0, "
            "worker_state = CASE WHEN enabled = 1 THEN 'IDLE' ELSE 'DISABLED' END, "
            "last_error = NULL "
            "WHERE id = 1"
        )
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ingestion_pending_tickets_requester_external_id"),
        table_name="ingestion_pending_tickets",
    )
    op.drop_index(
        op.f("ix_ingestion_pending_tickets_requester_email"),
        table_name="ingestion_pending_tickets",
    )
    op.drop_table("ingestion_pending_tickets")
