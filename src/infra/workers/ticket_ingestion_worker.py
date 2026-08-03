
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.application.dtos.ticket_ingestion import (
    IngestTicketBatchInput,
    TicketSourceRecord,
)
from src.bootstrap.composers.ingestion_control import (
    ingest_ticket_batch_composer,
)
from src.infra.database.repositories import SqlAlchemyTicketRepository
from src.infra.database.unit_of_work import UnitOfWork

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    source_path: Path
    batch_size: int
    interval_seconds: float
    poll_seconds: float

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        database_url = os.getenv("MYSQL_URL_CONNECTION_WORKER")
        if not database_url:
            raise RuntimeError("MYSQL_URL_CONNECTION_WORKER is required")
        return cls(
            database_url=database_url,
            source_path=Path(
                os.getenv("WORKER_SOURCE_PATH", "/data/tickets.json")
            ),
            batch_size=int(os.getenv("WORKER_BATCH_SIZE", "30")),
            interval_seconds=float(
                os.getenv("WORKER_INTERVAL_SECONDS", "30")
            ),
            poll_seconds=float(
                os.getenv("WORKER_CONTROL_POLL_SECONDS", "2")
            ),
        )


def read_ticket_source(path: Path) -> list[TicketSourceRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("tickets.json must contain a non-empty list")
    records = [TicketSourceRecord.model_validate(item) for item in payload]
    ticket_ids = [record.ticket_id for record in records]
    if len(ticket_ids) != len(set(ticket_ids)):
        raise ValueError("tickets.json contains duplicate ticket_id values")
    return records


async def run_cycle(
    engine: AsyncEngine,
    settings: Settings,
    source_records: list[TicketSourceRecord],
) -> bool | None:
    async with UnitOfWork(engine) as unit_of_work:
        repository = SqlAlchemyTicketRepository(unit_of_work)
        control = await repository.get_ingestion_control()

    if not control.enabled:
        return None

    source_total = len(source_records)
    start = control.cursor_position % source_total
    end = min(start + settings.batch_size, source_total)
    batch = source_records[start:end]

    async with UnitOfWork(engine) as unit_of_work:
        use_case = ingest_ticket_batch_composer(unit_of_work)
        result = await use_case.execute(
            IngestTicketBatchInput(
                expected_cursor=start,
                source_total=source_total,
                records=batch,
            )
        )

    LOGGER.info(
        "ticket_ingestion.completed received=%s matched_customers=%s "
        "ignored_unmonitored=%s identity_conflicts=%s created=%s "
        "updated=%s unchanged=%s next_cursor=%s",
        result.received,
        result.matched_customers,
        result.ignored_unmonitored,
        result.identity_conflicts,
        result.tickets_created,
        result.tickets_updated,
        result.tickets_unchanged,
        result.next_cursor,
    )
    return True


async def register_error(engine: AsyncEngine, error: Exception) -> None:
    async with UnitOfWork(engine) as unit_of_work:
        repository = SqlAlchemyTicketRepository(unit_of_work)
        await repository.register_ingestion_error(
            str(error) or type(error).__name__
        )


async def sleep_until_next_cycle(
    stop: asyncio.Event,
    seconds: float,
) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def run() -> None:
    settings = Settings.from_env()
    source_records = await asyncio.to_thread(
        read_ticket_source,
        settings.source_path,
    )
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop.set)
        except NotImplementedError:
            pass

    LOGGER.info(
        "ticket_ingestion.started batch_size=%s interval_seconds=%s "
        "source_records=%s source_path=%s",
        settings.batch_size,
        settings.interval_seconds,
        len(source_records),
        settings.source_path,
    )
    try:
        while not stop.is_set():
            try:
                completed = await run_cycle(
                    engine,
                    settings,
                    source_records,
                )
                delay = (
                    settings.poll_seconds
                    if completed is None
                    else settings.interval_seconds
                )
            except Exception as error:
                LOGGER.exception("ticket_ingestion.failed")
                try:
                    await register_error(engine, error)
                except Exception:
                    LOGGER.exception("ticket_ingestion.error_state_failed")
                delay = settings.interval_seconds
            await sleep_until_next_cycle(stop, delay)
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
