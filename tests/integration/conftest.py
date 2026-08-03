from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def _test_database_url() -> str:
    variable_name = "MYSQL_URL_CONNECTION_TEST"
    raw_url = os.getenv(variable_name)
    if not raw_url:
        raise RuntimeError(f"{variable_name} is required for integration tests")

    url = make_url(raw_url)
    if url.drivername != "mysql+aiomysql":
        raise RuntimeError(
            "Integration tests require the mysql+aiomysql driver"
        )
    if not url.database or not url.database.endswith("_test"):
        raise RuntimeError(
            "Integration tests refuse to use a database without the _test suffix"
        )
    for runtime_variable in (
        "MYSQL_URL_CONNECTION_API",
        "MYSQL_URL_CONNECTION_WORKER",
        "MYSQL_URL_CONNECTION_MIGRATIONS",
    ):
        runtime_url = os.getenv(runtime_variable)
        if not runtime_url:
            continue
        parsed_runtime_url = make_url(runtime_url)
        if (
            parsed_runtime_url.host,
            parsed_runtime_url.port,
            parsed_runtime_url.database,
        ) == (url.host, url.port, url.database):
            raise RuntimeError(
                f"{variable_name} must not match {runtime_variable}"
            )
    return raw_url


@pytest_asyncio.fixture(scope="session")
async def integration_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        _test_database_url(),
        pool_pre_ping=True,
    )
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    yield engine
    await engine.dispose()


async def _truncate_test_tables(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        table_names = list(
            (
                await connection.execute(
                    text(
                        "SELECT TABLE_NAME FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "AND TABLE_NAME <> 'alembic_version'"
                    )
                )
            ).scalars()
        )
        await connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        try:
            for table_name in table_names:
                safe_name = str(table_name).replace("`", "``")
                await connection.execute(text(f"TRUNCATE TABLE `{safe_name}`"))
        finally:
            await connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        await connection.commit()


@pytest_asyncio.fixture(autouse=True)
async def clean_integration_database(
    request: pytest.FixtureRequest,
    integration_engine: AsyncEngine,
) -> AsyncIterator[None]:
    if request.node.get_closest_marker("integration") is None:
        yield
        return

    await _truncate_test_tables(integration_engine)
    yield
    await _truncate_test_tables(integration_engine)
