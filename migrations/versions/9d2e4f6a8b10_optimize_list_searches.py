"""optimize ticket and customer list searches

Revision ID: 9d2e4f6a8b10
Revises: 8c1f2a6d9b40
Create Date: 2026-08-03 11:55:00

"""
from typing import Sequence, Union

from alembic import op

revision: str = "9d2e4f6a8b10"
down_revision: Union[str, Sequence[str], None] = "8c1f2a6d9b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_customers_requester_name_id",
        "customers",
        ["requester_name", "id"],
        unique=False,
    )
    op.create_index(
        "ix_tickets_assignee_name",
        "tickets",
        ["assignee_name"],
        unique=False,
    )
    op.create_index(
        "ft_tickets_subject_description",
        "tickets",
        ["subject", "description"],
        unique=False,
        mysql_prefix="FULLTEXT",
    )


def downgrade() -> None:
    op.drop_index("ft_tickets_subject_description", table_name="tickets")
    op.drop_index("ix_tickets_assignee_name", table_name="tickets")
    op.drop_index("ix_customers_requester_name_id", table_name="customers")
