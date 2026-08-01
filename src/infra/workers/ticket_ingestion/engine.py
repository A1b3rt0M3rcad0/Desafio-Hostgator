from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.infra.workers.ticket_ingestion.settings import WorkerSettings


@lru_cache(maxsize=1)
def get_worker_engine(settings: WorkerSettings) -> AsyncEngine:
    return create_async_engine(
        url=settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
