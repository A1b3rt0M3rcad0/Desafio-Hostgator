"""remove pending ingestion queue

Revision ID: c3f5a7b9d210
Revises: 9f4b7c2d1a60
Create Date: 2026-08-02 18:10:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3f5a7b9d210"
down_revision: Union[str, Sequence[str], None] = "9f4b7c2d1a60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("ingestion_pending_tickets")
    op.execute(
        sa.text(
            "UPDATE ingestion_control "
            "SET cursor_position = 0, source_version = NULL, "
            "worker_state = CASE WHEN enabled = 1 THEN 'IDLE' ELSE 'DISABLED' END, "
            "last_error = NULL WHERE id = 1"
        )
    )


def downgrade() -> None:
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
