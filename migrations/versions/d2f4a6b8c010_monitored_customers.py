"""add monitored customers and optional HelpDesk binding

Revision ID: d2f4a6b8c010
Revises: 5d8e7a1c2b30
Create Date: 2026-08-03 02:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2f4a6b8c010"
down_revision: Union[str, Sequence[str], None] = "5d8e7a1c2b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "customers",
        "external_requester_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.add_column(
        "customers",
        sa.Column(
            "is_monitored",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(
        "ix_customers_is_monitored",
        "customers",
        ["is_monitored"],
        unique=False,
    )
    op.execute(
        sa.text(
            "UPDATE ingestion_control SET cursor_position = 0, "
            "worker_state = CASE "
            "WHEN enabled = 1 THEN 'IDLE' ELSE 'DISABLED' END"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    null_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM customers "
            "WHERE external_requester_id IS NULL"
        )
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "Cannot downgrade while customers without external_requester_id exist"
        )

    op.drop_index("ix_customers_is_monitored", table_name="customers")
    op.drop_column("customers", "is_monitored")
    op.alter_column(
        "customers",
        "external_requester_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
