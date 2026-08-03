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

from data.generate_tickets_mock import generate_and_write_batch
from src.application.dtos.ticket_ingestion import TicketSourceRecord
from src.infra.database.repositories import (
    SqlAlchemyCustomerRepository,
    SqlAlchemySatisfactionRatingRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyTicketRepository,
    SqlAlchemyTicketTagRepository,
)
from src.infra.database.unit_of_work import UnitOfWork

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    source_path: Path
    batch_size: int
    interval_seconds: float
    poll_seconds: float
    customer_count: int
    start_ticket_id: int
    year: int
    seed: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        database_url = os.getenv("MYSQL_URL_CONNECTION_WORKER")
        if not database_url:
            raise RuntimeError("MYSQL_URL_CONNECTION_WORKER is required")
        return cls(
            database_url=database_url,
            source_path=Path(os.getenv("WORKER_SOURCE_PATH", "/data/tickets.json")),
            batch_size=int(os.getenv("WORKER_BATCH_SIZE", "30")),
            interval_seconds=float(os.getenv("WORKER_INTERVAL_SECONDS", "30")),
            poll_seconds=float(os.getenv("WORKER_CONTROL_POLL_SECONDS", "2")),
            customer_count=int(os.getenv("MOCK_CUSTOMER_COUNT", "500")),
            start_ticket_id=int(os.getenv("MOCK_START_TICKET_ID", "100001")),
            year=int(os.getenv("MOCK_YEAR", "2026")),
            seed=os.getenv("MOCK_SEED", "hostgator-challenge-v4"),
        )


def read_generated_tickets(path: Path, expected_count: int) -> list[TicketSourceRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != expected_count:
        raise ValueError(f"tickets.json must contain exactly {expected_count} records")
    return [TicketSourceRecord.model_validate(item) for item in payload]


async def run_cycle(engine: AsyncEngine, settings: Settings) -> bool:
    async with UnitOfWork(engine) as unit_of_work:
        customers = SqlAlchemyCustomerRepository(unit_of_work)
        tickets = SqlAlchemyTicketRepository(unit_of_work)
        tags = SqlAlchemyTagRepository(unit_of_work)
        ticket_tags = SqlAlchemyTicketTagRepository(unit_of_work)
        ratings = SqlAlchemySatisfactionRatingRepository(unit_of_work)

        control = await tickets.get_ingestion_control(for_update=True)
        if not control.enabled:
            return False

        generated_count = control.cursor_position
        cycle_number = generated_count // settings.batch_size
        start_ticket_id = settings.start_ticket_id + generated_count

        await asyncio.to_thread(
            generate_and_write_batch,
            output=settings.source_path,
            cycle_number=cycle_number,
            start_ticket_id=start_ticket_id,
            ticket_count=settings.batch_size,
            customer_count=settings.customer_count,
            year=settings.year,
            seed=settings.seed,
        )
        records = await asyncio.to_thread(
            read_generated_tickets,
            settings.source_path,
            settings.batch_size,
        )

        created_customers = 0
        created_tickets = 0
        for record in records:
            customer = await customers.upsert_from_source(
                external_requester_id=record.requester_id,
                requester_name=record.requester_name,
                requester_email=record.requester_email,
            )
            if customer.customer.id is None:
                raise RuntimeError("customer ID was not generated")

            ticket = await tickets.upsert_from_source(
                record,
                customer_id=customer.customer.id,
            )
            if ticket.ticket.id is None:
                raise RuntimeError("ticket ID was not generated")

            created_customers += int(customer.created)
            created_tickets += int(ticket.created)
            if ticket.unchanged:
                continue

            resolved_tags = await tags.resolve_by_names(record.tags)
            await ticket_tags.replace_for_ticket(
                ticket_id=ticket.ticket.id,
                tag_ids=[tag.id for tag in resolved_tags.values() if tag.id],
            )
            await ratings.synchronize_from_source(
                ticket_id=ticket.ticket.id,
                source=record.satisfaction_rating,
            )

        next_cursor = generated_count + len(records)
        await tickets.complete_ingestion_cycle(next_cursor=next_cursor)
        LOGGER.info(
            "ticket_ingestion.completed cycle=%s generated=%s customers_created=%s "
            "tickets_created=%s next_ticket_id=%s",
            cycle_number + 1,
            len(records),
            created_customers,
            created_tickets,
            settings.start_ticket_id + next_cursor,
        )
        return True


async def register_error(engine: AsyncEngine, error: Exception) -> None:
    async with UnitOfWork(engine) as unit_of_work:
        repository = SqlAlchemyTicketRepository(unit_of_work)
        await repository.register_ingestion_error(str(error) or type(error).__name__)


async def sleep_until_next_cycle(stop: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def run() -> None:
    settings = Settings.from_env()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop.set)
        except NotImplementedError:
            pass

    LOGGER.info(
        "ticket_ingestion.started batch_size=%s interval_seconds=%s customer_pool=%s",
        settings.batch_size,
        settings.interval_seconds,
        settings.customer_count,
    )
    try:
        while not stop.is_set():
            try:
                completed = await run_cycle(engine, settings)
                delay = (
                    settings.interval_seconds
                    if completed
                    else settings.poll_seconds
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
