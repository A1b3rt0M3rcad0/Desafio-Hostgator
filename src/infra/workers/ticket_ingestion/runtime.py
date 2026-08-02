from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from data.generate_tickets_mock import generate_and_write_batch
from src.infra.database.unit_of_work import UnitOfWork
from src.infra.ingestion.repositories import (
    SqlAlchemyIngestionControlRepository,
    SqlAlchemyTicketIngestionRepository,
)
from src.infra.ingestion.source import JsonTicketSourceRepository
from src.infra.workers.ticket_ingestion.settings import WorkerSettings

LOGGER = logging.getLogger(__name__)


class TicketIngestionWorker:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        source_repository: JsonTicketSourceRepository,
        settings: WorkerSettings,
    ) -> None:
        self._engine = engine
        self._source_repository = source_repository
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
            repository = SqlAlchemyIngestionControlRepository(unit_of_work)
            control = await repository.get_worker_control()
            return control.enabled

    async def _process_cycle(self) -> None:
        async with UnitOfWork(self._engine) as unit_of_work:
            control_repository = SqlAlchemyIngestionControlRepository(unit_of_work)
            ingestion_repository = SqlAlchemyTicketIngestionRepository(unit_of_work)
            control = await control_repository.get_worker_control(for_update=True)
            if not control.enabled:
                return

            await control_repository.mark_processing()
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
            batch = await asyncio.to_thread(
                self._source_repository.read_all,
                expected_count=self._settings.batch_size,
            )
            if batch.invalid:
                raise RuntimeError(
                    f"Generated JSON contains {batch.invalid} invalid record(s)"
                )

            result = await ingestion_repository.synchronize_batch(
                batch.records,
                received=batch.consumed,
            )
            if result.unmatched or result.conflicted:
                raise RuntimeError(
                    "Generated customer identity conflict: "
                    f"unmatched={result.unmatched}, conflicted={result.conflicted}"
                )

            next_cursor = generated_count + batch.consumed
            await control_repository.complete_batch(
                next_cursor=next_cursor,
                source_version=digest,
                exhausted=False,
            )

            LOGGER.info(
                "ticket_ingestion.cycle.completed cycle=%s generated=%s "
                "customers_created=%s customers_updated=%s tickets_created=%s "
                "tickets_updated=%s unchanged=%s next_ticket_id=%s json_sha256=%s",
                cycle_number + 1,
                len(generated),
                result.customers_created,
                result.customers_updated,
                result.created,
                result.updated,
                result.unchanged,
                self._settings.mock_start_ticket_id + next_cursor,
                digest,
            )

    async def _register_error(self, error: Exception) -> None:
        try:
            async with UnitOfWork(self._engine) as unit_of_work:
                repository = SqlAlchemyIngestionControlRepository(unit_of_work)
                await repository.register_error(str(error) or error.__class__.__name__)
        except Exception:
            LOGGER.exception("ticket_ingestion.worker.error_state_failed")

    async def _sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._shutdown.wait(), timeout=seconds)
        except TimeoutError:
            pass
