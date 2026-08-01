from __future__ import annotations

import os
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def main() -> int:
    database_url = os.getenv("MYSQL_URL_CONNECTION_MIGRATIONS", "").strip()
    if not database_url:
        print("MYSQL_URL_CONNECTION_MIGRATIONS is required", file=sys.stderr)
        return 1

    timeout_seconds = float(os.getenv("DB_WAIT_TIMEOUT_SECONDS", "90"))
    interval_seconds = float(os.getenv("DB_WAIT_INTERVAL_SECONDS", "2"))
    deadline = time.monotonic() + timeout_seconds
    attempt = 0

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        while True:
            attempt += 1
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                print(f"Database is ready after {attempt} attempt(s)")
                return 0
            except SQLAlchemyError as error:
                if time.monotonic() >= deadline:
                    print(
                        f"Database was not ready within {timeout_seconds:.0f}s: {error}",
                        file=sys.stderr,
                    )
                    return 1

                print(
                    f"Database not ready (attempt {attempt}); retrying in "
                    f"{interval_seconds:g}s"
                )
                time.sleep(interval_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
