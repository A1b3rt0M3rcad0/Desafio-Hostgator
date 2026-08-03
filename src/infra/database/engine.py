import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_engine() -> AsyncEngine:
    load_dotenv()
    url = os.getenv("MYSQL_URL_CONNECTION_API")
    if url is None:
        raise ValueError("MYSQL_URL_CONNECTION_API environment variable is not set.")
    return create_async_engine(
        url=url,
        echo=_env_bool("SQL_ECHO", default=False),
        pool_pre_ping=True,
    )
