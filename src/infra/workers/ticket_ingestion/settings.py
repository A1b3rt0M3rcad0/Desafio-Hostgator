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
    mock_customer_count: int = 500
    mock_start_ticket_id: int = 100_001
    mock_year: int = 2026
    mock_seed: str = "hostgator-challenge-v4"

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
            mock_customer_count=int(os.getenv("MOCK_CUSTOMER_COUNT", "500")),
            mock_start_ticket_id=int(os.getenv("MOCK_START_TICKET_ID", "100001")),
            mock_year=int(os.getenv("MOCK_YEAR", "2026")),
            mock_seed=os.getenv("MOCK_SEED", "hostgator-challenge-v4"),
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
        if self.mock_start_ticket_id <= 0:
            raise ValueError("MOCK_START_TICKET_ID must be greater than zero")
        if self.mock_customer_count <= 0:
            raise ValueError("MOCK_CUSTOMER_COUNT must be greater than zero")
        if self.batch_size > self.mock_customer_count:
            raise ValueError(
                "WORKER_BATCH_SIZE cannot be greater than MOCK_CUSTOMER_COUNT"
            )
        if self.mock_year < 2000 or self.mock_year > 2100:
            raise ValueError("MOCK_YEAR must be between 2000 and 2100")
        if not self.mock_seed:
            raise ValueError("MOCK_SEED cannot be empty")
