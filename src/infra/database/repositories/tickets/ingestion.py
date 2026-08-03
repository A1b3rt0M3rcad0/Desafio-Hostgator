from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from src.application.dtos.ingestion_control import IngestionControlState
from src.application.dtos.ticket_ingestion import TicketSourceRecord, TicketSourceResult
from src.domain.entities import TicketEntity
from src.infra.database.models import IngestionControl, Ticket
from src.infra.database.repositories.common import naive_utc as _naive_utc
from src.infra.database.repositories.tickets.base import TicketRepositoryMixinBase


class TicketIngestionMixin(TicketRepositoryMixinBase):
    async def upsert_from_source(
        self,
        record: TicketSourceRecord,
        *,
        customer_id: UUID,
    ) -> TicketSourceResult:
        ticket = (
            await self._session.execute(
                select(Ticket)
                .where(Ticket.external_ticket_id == record.ticket_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        source_updated_at = _naive_utc(record.updated_at)

        if ticket is not None and ticket.source_updated_at >= source_updated_at:
            return TicketSourceResult(
                ticket=TicketEntity.model_validate(ticket),
                unchanged=True,
            )

        values = {
            "customer_id": customer_id,
            "subject": record.subject,
            "description": record.description,
            "first_response_at": _naive_utc(record.first_response_at),
            "status": record.status,
            "priority": record.priority,
            "assignee_external_id": record.assignee_id,
            "assignee_name": record.assignee_name,
            "source_created_at": _naive_utc(record.created_at),
            "source_updated_at": source_updated_at,
        }
        created = ticket is None
        if ticket is None:
            ticket = Ticket(external_ticket_id=record.ticket_id, **values)
            self._session.add(ticket)
        else:
            for key, value in values.items():
                setattr(ticket, key, value)

        await self._session.flush()
        return TicketSourceResult(
            ticket=TicketEntity.model_validate(ticket),
            created=created,
        )

    async def get_ingestion_control(
        self,
        *,
        for_update: bool = False,
    ) -> IngestionControlState:
        control = await self._get_ingestion_control_model(for_update=for_update)
        return self._to_ingestion_control_state(control)

    async def set_ingestion_enabled(
        self,
        enabled: bool,
    ) -> IngestionControlState:
        control = await self._get_ingestion_control_model(for_update=True)
        control.enabled = enabled
        control.worker_state = "IDLE" if enabled else "DISABLED"
        if enabled:
            control.last_error = None
        await self._session.flush()
        return self._to_ingestion_control_state(control)

    async def complete_ingestion_cycle(self, *, next_cursor: int) -> None:
        control = await self._get_ingestion_control_model(for_update=True)
        now = self._now()
        control.cursor_position = next_cursor
        control.worker_state = "IDLE"
        control.last_heartbeat_at = now
        control.last_success_at = now
        control.last_error = None
        await self._session.flush()

    async def register_ingestion_error(self, message: str) -> None:
        control = await self._get_ingestion_control_model(for_update=True)
        control.worker_state = "ERROR"
        control.last_heartbeat_at = self._now()
        control.last_error = message[:2000]
        await self._session.flush()

    async def _get_ingestion_control_model(
        self,
        *,
        for_update: bool = False,
    ) -> IngestionControl:
        stmt = select(IngestionControl).where(IngestionControl.id == 1)
        if for_update:
            stmt = stmt.with_for_update()
        control = (await self._session.execute(stmt)).scalar_one_or_none()
        if control is None:
            control = IngestionControl(id=1)
            self._session.add(control)
            await self._session.flush()
        return control

    @staticmethod
    def _to_ingestion_control_state(
        control: IngestionControl,
    ) -> IngestionControlState:
        return IngestionControlState(
            enabled=control.enabled,
            worker_state=control.worker_state,
            cursor_position=control.cursor_position,
            last_heartbeat_at=control.last_heartbeat_at,
            last_success_at=control.last_success_at,
            last_error=control.last_error,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
