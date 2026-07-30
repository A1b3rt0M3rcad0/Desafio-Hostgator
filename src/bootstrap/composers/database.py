from sqlalchemy.ext.asyncio import AsyncEngine

from src.infra.database.engine import get_engine


DATABASE_ENGINE: AsyncEngine = get_engine()
