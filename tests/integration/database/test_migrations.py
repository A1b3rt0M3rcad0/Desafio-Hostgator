import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_migrations_create_expected_schema_at_head(
    integration_engine: AsyncEngine,
) -> None:
    async with integration_engine.connect() as connection:
        revision = (
            await connection.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()
        tables = set(
            (
                await connection.execute(
                    text(
                        "SELECT TABLE_NAME FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE()"
                    )
                )
            ).scalars()
        )

    assert revision == "9d2e4f6a8b10"
    assert {
        "alembic_version",
        "auth_sessions",
        "customers",
        "ingestion_control",
        "satisfaction_ratings",
        "tags",
        "ticket_tags",
        "tickets",
        "users",
    }.issubset(tables)
