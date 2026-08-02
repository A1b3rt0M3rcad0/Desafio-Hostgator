from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    database_url: str
    source_path: str
    batch_size: int = 30
    interval_seconds: float = 30.0
    control_poll_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> WorkerSettings:
        load_dotenv()
        database_url = os.getenv("MYSQL_URL_CONNECTION_WORKER")
        if not database_url:
            raise ValueError(
                "MYSQL_URL_CONNECTION_WORKER environment variable is not set."
            )

        settings = cls(
            database_url=database_url,
            source_path=os.getenv("WORKER_SOURCE_PATH", "/data/tickets.json"),
            batch_size=int(os.getenv("WORKER_BATCH_SIZE", "30")),
            interval_seconds=float(os.getenv("WORKER_INTERVAL_SECONDS", "30")),
            control_poll_seconds=float(
                os.getenv("WORKER_CONTROL_POLL_SECONDS", "2")
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.batch_size <= 0:
            raise ValueError("WORKER_BATCH_SIZE must be greater than zero")
        if self.interval_seconds <= 0:
            raise ValueError("WORKER_INTERVAL_SECONDS must be greater than zero")
        if self.control_poll_seconds <= 0:
            raise ValueError(
                "WORKER_CONTROL_POLL_SECONDS must be greater than zero"
            )
