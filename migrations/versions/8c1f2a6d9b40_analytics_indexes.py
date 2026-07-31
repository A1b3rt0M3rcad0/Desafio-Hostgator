"""add analytical query indexes

Revision ID: 8c1f2a6d9b40
Revises: 7b7c4d4e2f10
Create Date: 2026-07-31 16:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8c1f2a6d9b40"
down_revision: Union[str, Sequence[str], None] = "7b7c4d4e2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ix_tickets_source_created_at", ("source_created_at",)),
    ("ix_tickets_customer_source_created_at", ("customer_id", "source_created_at")),
    ("ix_tickets_status_source_created_at", ("status", "source_created_at")),
    ("ix_tickets_priority_source_created_at", ("priority", "source_created_at")),
    ("ix_tickets_assignee_source_created_at", ("assignee_external_id", "source_created_at")),
)


def _index_names(bind: sa.Connection) -> set[str]:
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes("tickets")}


def upgrade() -> None:
    bind = op.get_bind()
    existing = _index_names(bind)
    for name, columns in _INDEXES:
        if name not in existing:
            op.create_index(name, "tickets", list(columns), unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    existing = _index_names(bind)
    for name, _ in reversed(_INDEXES):
        if name in existing:
            op.drop_index(name, table_name="tickets")
