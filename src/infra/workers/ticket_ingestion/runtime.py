from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from data.generate_tickets_mock import generate_and_write_batch
from src.infra.database.repositories import (
    SqlAlchemyCustomerRepository,
    SqlAlchemySatisfactionRatingRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyTicketRepository,
    SqlAlchemyTicketTagRepository,
)
from src.infra.database.unit_of_work import UnitOfWork
from src.infra.ingestion.source import read_ticket_source
from src.infra.workers.ticket_ingestion.settings import WorkerSettings

LOGGER = logging.getLogger(__name__)


class TicketIngestionWorker:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        settings: WorkerSettings,
    ) -> None:
        self._engine = engine
        self._settings = settings
        self._shutdown = asyncio.Event()

    def request_shutdown(self) -> None:
        self._shutdown.set()

    async def run(self) -> None:
        LOGGER.info(
            "ticket_ingestion.worker.started batch_size=%s interval_seconds=%s "
            "customer_pool=%s",
            self._settings.batch_size,
            self._settings.interval_seconds,
            self._settings.mock_customer_count,
        )
        while not self._shutdown.is_set():
            try:
                if not await self._is_enabled():
                    await self._sleep(self._settings.control_poll_seconds)
                    continue
                await self._process_cycle()
                await self._sleep(self._settings.interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                LOGGER.exception("ticket_ingestion.worker.failed")
                await self._register_error(error)
                await self._sleep(self._settings.interval_seconds)
        LOGGER.info("ticket_ingestion.worker.stopped")

    async def _is_enabled(self) -> bool:
        async with UnitOfWork(self._engine) as unit_of_work:
            repository = SqlAlchemyTicketRepository(unit_of_work)
            control = await repository.get_ingestion_control()
            return control.enabled

    async def _process_cycle(self) -> None:
        async with UnitOfWork(self._engine) as unit_of_work:
            customer_repository = SqlAlchemyCustomerRepository(unit_of_work)
            ticket_repository = SqlAlchemyTicketRepository(unit_of_work)
            tag_repository = SqlAlchemyTagRepository(unit_of_work)
            ticket_tag_repository = SqlAlchemyTicketTagRepository(unit_of_work)
            satisfaction_repository = SqlAlchemySatisfactionRatingRepository(
                unit_of_work
            )

            control = await ticket_repository.get_ingestion_control(for_update=True)
            if not control.enabled:
                return

            await ticket_repository.mark_ingestion_processing()
            generated_count = control.cursor_position
            cycle_number = generated_count // self._settings.batch_size
            start_ticket_id = self._settings.mock_start_ticket_id + generated_count

            generated, digest = await asyncio.to_thread(
                generate_and_write_batch,
                output=self._settings.source_path,
                cycle_number=cycle_number,
                start_ticket_id=start_ticket_id,
                ticket_count=self._settings.batch_size,
                customer_count=self._settings.mock_customer_count,
                year=self._settings.mock_year,
                seed=self._settings.mock_seed,
            )
            records = await asyncio.to_thread(
                read_ticket_source,
                self._settings.source_path,
                expected_count=self._settings.batch_size,
            )

            customers_created = 0
            customers_updated = 0
            tickets_created = 0
            tickets_updated = 0
            tickets_unchanged = 0

            for record in records:
                customer_result = await customer_repository.upsert_from_source(
                    external_requester_id=record.requester_id,
                    requester_name=record.requester_name,
                    requester_email=record.requester_email,
                )
                customer_id = customer_result.customer.id
                if customer_id is None:
                    raise RuntimeError("Customer repository returned an empty ID")

                ticket_result = await ticket_repository.upsert_from_source(
                    record,
                    customer_id=customer_id,
                )
                ticket_id = ticket_result.ticket.id
                if ticket_id is None:
                    raise RuntimeError("Ticket repository returned an empty ID")

                customers_created += int(customer_result.created)
                customers_updated += int(customer_result.updated)
                tickets_created += int(ticket_result.created)
                tickets_updated += int(ticket_result.updated)
                tickets_unchanged += int(ticket_result.unchanged)

                if ticket_result.unchanged:
                    continue

                tags = await tag_repository.resolve_by_names(record.tags)
                await ticket_tag_repository.replace_for_ticket(
                    ticket_id=ticket_id,
                    tag_ids=[tag.id for tag in tags.values() if tag.id is not None],
                )
                await satisfaction_repository.synchronize_from_source(
                    ticket_id=ticket_id,
                    source=record.satisfaction_rating,
                )

            next_cursor = generated_count + len(records)
            await ticket_repository.complete_ingestion_cycle(
                next_cursor=next_cursor,
                source_version=digest,
            )

            LOGGER.info(
                "ticket_ingestion.cycle.completed cycle=%s generated=%s "
                "customers_created=%s customers_updated=%s tickets_created=%s "
                "tickets_updated=%s unchanged=%s next_ticket_id=%s json_sha256=%s",
                cycle_number + 1,
                len(generated),
                customers_created,
                customers_updated,
                tickets_created,
                tickets_updated,
                tickets_unchanged,
                self._settings.mock_start_ticket_id + next_cursor,
                digest,
            )

    async def _register_error(self, error: Exception) -> None:
        try:
            async with UnitOfWork(self._engine) as unit_of_work:
                repository = SqlAlchemyTicketRepository(unit_of_work)
                await repository.register_ingestion_error(
                    str(error) or error.__class__.__name__
                )
        except Exception:
            LOGGER.exception("ticket_ingestion.worker.error_state_failed")

    async def _sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._shutdown.wait(), timeout=seconds)
        except TimeoutError:
            pass
