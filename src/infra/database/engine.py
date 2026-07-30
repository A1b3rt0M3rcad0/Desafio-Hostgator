from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from dotenv import load_dotenv
import os

def get_engine() -> AsyncEngine:
    load_dotenv()
    url = os.getenv("MYSQL_URL_CONNECTION_API")
    if url is None:
        raise ValueError("MYSQL_URL_CONNECTION_API environment variable is not set.")
    engine = create_async_engine(url=url, echo=True, pool_pre_ping=True)
    return engine