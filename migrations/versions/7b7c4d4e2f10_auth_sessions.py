"""add authentication sessions

Revision ID: 7b7c4d4e2f10
Revises: 4fcbc8dd1a8b
Create Date: 2026-07-31 11:42:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "7b7c4d4e2f10"
down_revision: Union[str, Sequence[str], None] = "4fcbc8dd1a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind: sa.Connection, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names()


def _column_exists(bind: sa.Connection, table_name: str, column_name: str) -> bool:
    if not _table_exists(bind, table_name):
        return False
    return column_name in {
        column["name"] for column in sa.inspect(bind).get_columns(table_name)
    }


def _index_names(bind: sa.Connection, table_name: str) -> set[str]:
    if not _table_exists(bind, table_name):
        return set()

    inspector = sa.inspect(bind)
    names = {
        index["name"]
        for index in inspector.get_indexes(table_name)
        if index.get("name")
    }
    names.update(
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    )
    return names


def upgrade() -> None:
    bind = op.get_bind()

    # MySQL DDL is not fully transactional. These checks allow this migration
    # to resume safely if a previous attempt already dropped the old column or
    # created the user email index before failing later in the migration.
    if _column_exists(bind, "users", "refresh_token"):
        op.drop_column("users", "refresh_token")

    if "ix_users_email" not in _index_names(bind, "users"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not _table_exists(bind, "auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column(
                "refresh_token_hash",
                mysql.BINARY(length=32),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("compromised_at", sa.DateTime(), nullable=True),
            sa.Column("rotation_counter", sa.Integer(), nullable=False),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "refresh_token_hash",
                name="uq_auth_sessions_refresh_token_hash",
            ),
        )
    else:
        columns = {
            column["name"]: column
            for column in sa.inspect(bind).get_columns("auth_sessions")
        }
        refresh_hash_column = columns.get("refresh_token_hash")
        if refresh_hash_column is None:
            op.add_column(
                "auth_sessions",
                sa.Column(
                    "refresh_token_hash",
                    mysql.BINARY(length=32),
                    nullable=False,
                ),
            )
        else:
            current_type = refresh_hash_column["type"]
            if not isinstance(current_type, sa.BINARY) or current_type.length != 32:
                op.alter_column(
                    "auth_sessions",
                    "refresh_token_hash",
                    existing_type=current_type,
                    type_=mysql.BINARY(length=32),
                    existing_nullable=False,
                )

    auth_session_indexes = _index_names(bind, "auth_sessions")
    if "ix_auth_sessions_user_id" not in auth_session_indexes:
        op.create_index(
            "ix_auth_sessions_user_id",
            "auth_sessions",
            ["user_id"],
            unique=False,
        )

    if "uq_auth_sessions_refresh_token_hash" not in _index_names(
        bind,
        "auth_sessions",
    ):
        op.create_index(
            "uq_auth_sessions_refresh_token_hash",
            "auth_sessions",
            ["refresh_token_hash"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _table_exists(bind, "auth_sessions"):
        op.drop_table("auth_sessions")

    if "ix_users_email" in _index_names(bind, "users"):
        op.drop_index("ix_users_email", table_name="users")

    if not _column_exists(bind, "users", "refresh_token"):
        op.add_column(
            "users",
            sa.Column(
                "refresh_token",
                sa.String(length=1024),
                nullable=False,
                server_default="",
            ),
        )
        op.alter_column(
            "users",
            "refresh_token",
            existing_type=sa.String(length=1024),
            existing_nullable=False,
            server_default=None,
        )
