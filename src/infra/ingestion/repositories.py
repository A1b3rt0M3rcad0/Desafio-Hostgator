from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.contracts.ingestion_control import IngestionControlRepository
from src.application.dtos.ingestion_control import IngestionControlState
from src.infra.database.models import (
    Customer,
    IngestionControl,
    SatisfactionRating,
    Tag,
    Ticket,
    TicketTag,
)
from src.infra.database.unit_of_work import UnitOfWork
from src.infra.ingestion.schemas import (
    BatchIngestionResult,
    TicketSourceRecord,
    WorkerControl,
)


class _SqlAlchemyIngestionRepository:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    @property
    def _session(self) -> AsyncSession:
        return self._unit_of_work.session


class SqlAlchemyIngestionControlRepository(
    _SqlAlchemyIngestionRepository,
    IngestionControlRepository,
):
    async def get(self) -> IngestionControlState:
        return self._to_public_state(await self._get_model())

    async def set_enabled(self, enabled: bool) -> IngestionControlState:
        control = await self._get_model(for_update=True)
        control.enabled = enabled
        control.worker_state = "IDLE" if enabled else "DISABLED"
        if enabled:
            control.last_error = None
        await self._session.flush()
        return self._to_public_state(control)

    async def get_worker_control(self, *, for_update: bool = False) -> WorkerControl:
        control = await self._get_model(for_update=for_update)
        return WorkerControl(
            **self._to_public_state(control).model_dump(),
            source_version=control.source_version,
        )

    async def mark_processing(self) -> None:
        control = await self._get_model(for_update=True)
        control.worker_state = "PROCESSING"
        control.last_heartbeat_at = self._now()
        control.last_error = None
        await self._session.flush()

    async def complete_batch(
        self,
        *,
        next_cursor: int,
        source_version: str,
        exhausted: bool,
    ) -> None:
        control = await self._get_model(for_update=True)
        control.cursor_position = next_cursor
        control.source_version = source_version
        control.worker_state = "CAUGHT_UP" if exhausted else "IDLE"
        control.last_heartbeat_at = self._now()
        control.last_success_at = self._now()
        control.last_error = None
        await self._session.flush()

    async def reset_source(self, source_version: str) -> None:
        control = await self._get_model(for_update=True)
        control.cursor_position = 0
        control.source_version = source_version
        control.worker_state = "IDLE"
        control.last_error = None
        await self._session.flush()

    async def register_error(self, message: str) -> None:
        control = await self._get_model(for_update=True)
        control.worker_state = "ERROR"
        control.last_heartbeat_at = self._now()
        control.last_error = message[:2000]
        await self._session.flush()

    async def _get_model(self, *, for_update: bool = False) -> IngestionControl:
        statement = select(IngestionControl).where(IngestionControl.id == 1)
        if for_update:
            statement = statement.with_for_update()
        control = (await self._session.execute(statement)).scalar_one_or_none()
        if control is None:
            control = IngestionControl(id=1)
            self._session.add(control)
            await self._session.flush()
        return control

    @staticmethod
    def _to_public_state(control: IngestionControl) -> IngestionControlState:
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


class SqlAlchemyTicketIngestionRepository(_SqlAlchemyIngestionRepository):
    async def synchronize_batch(
        self,
        records: list[TicketSourceRecord],
        *,
        invalid: int = 0,
        received: int | None = None,
    ) -> BatchIngestionResult:
        deduplicated = self._deduplicate(records)
        (
            customers,
            customers_created,
            customers_updated,
            conflicted,
        ) = await self._upsert_customers(deduplicated)

        matched: list[tuple[TicketSourceRecord, Customer]] = []
        for record in deduplicated:
            customer = customers.get(record.requester_email)
            if customer is not None:
                matched.append((record, customer))

        external_ids = [record.ticket_id for record, _ in matched]
        existing_tickets: list[Ticket] = []
        if external_ids:
            existing_tickets = (
                await self._session.execute(
                    select(Ticket).where(Ticket.external_ticket_id.in_(external_ids))
                )
            ).scalars().all()
        tickets_by_external_id = {
            ticket.external_ticket_id: ticket for ticket in existing_tickets
        }

        created = 0
        updated = 0
        unchanged = len(records) - len(deduplicated)
        changed: list[tuple[Ticket, TicketSourceRecord]] = []

        for record, customer in matched:
            ticket = tickets_by_external_id.get(record.ticket_id)
            source_updated_at = self._naive_utc(record.updated_at)
            if ticket is not None and ticket.source_updated_at >= source_updated_at:
                unchanged += 1
                continue

            values = {
                "customer_id": customer.id,
                "subject": record.subject,
                "description": record.description,
                "first_response_at": self._naive_utc(record.first_response_at),
                "status": record.status,
                "priority": record.priority,
                "assignee_external_id": record.assignee_id,
                "assignee_name": record.assignee_name,
                "source_created_at": self._naive_utc(record.created_at),
                "source_updated_at": source_updated_at,
            }
            if ticket is None:
                ticket = Ticket(external_ticket_id=record.ticket_id, **values)
                self._session.add(ticket)
                tickets_by_external_id[record.ticket_id] = ticket
                created += 1
            else:
                for key, value in values.items():
                    setattr(ticket, key, value)
                updated += 1
            changed.append((ticket, record))

        await self._session.flush()
        if changed:
            tags = await self._resolve_tags(changed)
            await self._replace_tags(changed, tags)
            await self._replace_satisfaction(changed)
            await self._session.flush()

        return BatchIngestionResult(
            received=received if received is not None else len(records) + invalid,
            customers_created=customers_created,
            customers_updated=customers_updated,
            created=created,
            updated=updated,
            unchanged=unchanged,
            unmatched=0,
            conflicted=conflicted,
            invalid=invalid,
        )

    async def _upsert_customers(
        self,
        records: list[TicketSourceRecord],
    ) -> tuple[dict[str, Customer], int, int, int]:
        identities: dict[str, TicketSourceRecord] = {}
        source_ids: dict[int, str] = {}
        conflicted = 0

        for record in records:
            current = identities.get(record.requester_email)
            if current is not None and current.requester_id != record.requester_id:
                conflicted += 1
                continue
            current_email = source_ids.get(record.requester_id)
            if current_email is not None and current_email != record.requester_email:
                conflicted += 1
                continue
            identities[record.requester_email] = record
            source_ids[record.requester_id] = record.requester_email

        emails = set(identities)
        external_ids = {record.requester_id for record in identities.values()}
        existing: list[Customer] = []
        if emails or external_ids:
            existing = (
                await self._session.execute(
                    select(Customer).where(
                        or_(
                            func.lower(Customer.requester_email).in_(emails),
                            Customer.external_requester_id.in_(external_ids),
                        )
                    )
                )
            ).scalars().all()

        by_email = {
            customer.requester_email.strip().lower(): customer
            for customer in existing
        }
        by_external_id = {
            customer.external_requester_id: customer for customer in existing
        }
        resolved: dict[str, Customer] = {}
        created = 0
        updated = 0

        for email, record in identities.items():
            email_match = by_email.get(email)
            id_match = by_external_id.get(record.requester_id)

            if (
                email_match is not None
                and id_match is not None
                and email_match.id != id_match.id
            ):
                conflicted += 1
                continue
            customer = email_match or id_match
            if customer is not None:
                if (
                    customer.requester_email.strip().lower() != email
                    or customer.external_requester_id != record.requester_id
                ):
                    conflicted += 1
                    continue
                if customer.requester_name != record.requester_name:
                    customer.requester_name = record.requester_name
                    updated += 1
            else:
                customer = Customer(
                    external_requester_id=record.requester_id,
                    requester_name=record.requester_name,
                    requester_email=email,
                )
                self._session.add(customer)
                by_email[email] = customer
                by_external_id[record.requester_id] = customer
                created += 1
            resolved[email] = customer

        await self._session.flush()
        return resolved, created, updated, conflicted

    async def _resolve_tags(
        self,
        changed: list[tuple[Ticket, TicketSourceRecord]],
    ) -> dict[str, Tag]:
        names = {name for _, record in changed for name in record.tags}
        if not names:
            return {}
        existing = (
            await self._session.execute(select(Tag).where(Tag.name.in_(names)))
        ).scalars().all()
        by_name = {tag.name: tag for tag in existing}
        for name in sorted(names):
            if name not in by_name:
                tag = Tag(name=name)
                self._session.add(tag)
                by_name[name] = tag
        await self._session.flush()
        return by_name

    async def _replace_tags(
        self,
        changed: list[tuple[Ticket, TicketSourceRecord]],
        tags: dict[str, Tag],
    ) -> None:
        ticket_ids = [ticket.id for ticket, _ in changed]
        await self._session.execute(
            delete(TicketTag).where(TicketTag.ticket_id.in_(ticket_ids))
        )
        for ticket, record in changed:
            for tag_name in record.tags:
                self._session.add(
                    TicketTag(ticket_id=ticket.id, tag_id=tags[tag_name].id)
                )

    async def _replace_satisfaction(
        self,
        changed: list[tuple[Ticket, TicketSourceRecord]],
    ) -> None:
        ticket_ids = [ticket.id for ticket, _ in changed]
        existing = (
            await self._session.execute(
                select(SatisfactionRating).where(
                    SatisfactionRating.ticket_id.in_(ticket_ids)
                )
            )
        ).scalars().all()
        by_ticket_id = {rating.ticket_id: rating for rating in existing}

        for ticket, record in changed:
            current = by_ticket_id.get(ticket.id)
            imported = record.satisfaction_rating
            if imported is None:
                if current is not None:
                    await self._session.delete(current)
                continue

            values = {
                "score": imported.score,
                "offered_at": self._naive_utc(imported.offered_at),
                "rated_at": self._naive_utc(imported.rated_at),
                "comment": imported.comment,
            }
            if current is None:
                self._session.add(SatisfactionRating(ticket_id=ticket.id, **values))
            else:
                for key, value in values.items():
                    setattr(current, key, value)

    @staticmethod
    def _deduplicate(records: list[TicketSourceRecord]) -> list[TicketSourceRecord]:
        latest: dict[int, TicketSourceRecord] = {}
        for record in records:
            current = latest.get(record.ticket_id)
            if current is None or record.updated_at >= current.updated_at:
                latest[record.ticket_id] = record
        return [latest[ticket_id] for ticket_id in sorted(latest)]

    @staticmethod
    def _naive_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
