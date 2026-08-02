from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncEngine

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
            "ticket_ingestion.worker.started batch_size=%s interval_seconds=%s",
            self._settings.batch_size,
            self._settings.interval_seconds,
        )
        while not self._shutdown.is_set():
            try:
                if not await self._is_enabled():
                    await self._sleep(self._settings.control_poll_seconds)
                    continue
                await self._process_next_batch()
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

    async def _process_next_batch(self) -> None:
        async with UnitOfWork(self._engine) as unit_of_work:
            control_repository = SqlAlchemyIngestionControlRepository(unit_of_work)
            ingestion_repository = SqlAlchemyTicketIngestionRepository(unit_of_work)
            control = await control_repository.get_worker_control(for_update=True)
            if not control.enabled:
                return

            source_version = await asyncio.to_thread(
                self._source_repository.current_version
            )
            cursor = control.cursor_position
            if control.source_version != source_version:
                await control_repository.reset_source(source_version)
                cursor = 0

            await control_repository.mark_processing()
            batch = await asyncio.to_thread(
                self._source_repository.read_batch,
                cursor,
                self._settings.batch_size,
            )
            result = await ingestion_repository.synchronize_batch(
                batch.records,
                invalid=batch.invalid,
                received=batch.consumed,
            )
            next_cursor = cursor + batch.consumed
            await control_repository.complete_batch(
                next_cursor=next_cursor,
                source_version=batch.version,
                exhausted=batch.exhausted,
            )

            LOGGER.info(
                "ticket_ingestion.batch.completed cursor=%s next_cursor=%s "
                "received=%s created=%s updated=%s unchanged=%s unmatched=%s "
                "conflicted=%s invalid=%s exhausted=%s",
                cursor,
                next_cursor,
                result.received,
                result.created,
                result.updated,
                result.unchanged,
                result.unmatched,
                result.conflicted,
                result.invalid,
                batch.exhausted,
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
