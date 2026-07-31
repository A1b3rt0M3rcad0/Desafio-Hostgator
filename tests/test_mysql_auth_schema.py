from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from src.infra.database.models import AuthSession


def test_refresh_token_hash_uses_indexable_fixed_binary_on_mysql() -> None:
    ddl = str(
        CreateTable(AuthSession.__table__).compile(
            dialect=mysql.dialect(),
        ),
    )

    assert "refresh_token_hash BINARY(32) NOT NULL" in ddl
    assert "refresh_token_hash BLOB" not in ddl
    assert "uq_auth_sessions_refresh_token_hash" in ddl
