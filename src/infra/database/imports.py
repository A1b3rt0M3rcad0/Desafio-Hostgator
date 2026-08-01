from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.contracts.analytics import TicketImportRepository
from src.application.dtos.imports import SyncTicketsOutput, TicketImportRecord
from src.infra.database.models import Customer, SatisfactionRating, Tag, Ticket, TicketTag
from src.infra.database.unit_of_work import UnitOfWork


class SqlAlchemyTicketImportRepository(TicketImportRepository):
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    @property
    def _session(self) -> AsyncSession:
        return self._unit_of_work.session

    async def sync(self, records: list[TicketImportRecord]) -> SyncTicketsOutput:
        deduplicated = self._deduplicate(records)
        customers, customers_created = await self._resolve_customers(deduplicated)
        tags, tags_created = await self._resolve_tags(deduplicated)

        external_ticket_ids = [record.ticket_id for record in deduplicated]
        existing_tickets = (
            await self._session.execute(
                select(Ticket).where(Ticket.external_ticket_id.in_(external_ticket_ids))
            )
        ).scalars().all()
        tickets_by_external_id = {ticket.external_ticket_id: ticket for ticket in existing_tickets}

        created = 0
        updated = 0
        unchanged = 0
        changed: list[tuple[Ticket, TicketImportRecord]] = []
        for record in deduplicated:
            customer = customers[record.requester_email]
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
            await self._replace_tags(changed, tags)
            await self._replace_satisfaction(changed)
        await self._session.flush()

        return SyncTicketsOutput(
            received=len(records),
            created=created,
            updated=updated,
            unchanged=unchanged + (len(records) - len(deduplicated)),
            customers_created=customers_created,
            tags_created=tags_created,
            failed=0,
        )

    async def _resolve_customers(
        self,
        records: list[TicketImportRecord],
    ) -> tuple[dict[str, Customer], int]:
        emails = {record.requester_email for record in records}
        external_ids = {record.requester_id for record in records}
        existing = (
            await self._session.execute(
                select(Customer).where(
                    or_(
                        Customer.requester_email.in_(emails),
                        Customer.external_requester_id.in_(external_ids),
                    )
                )
            )
        ).scalars().all()
        by_email = {customer.requester_email.lower(): customer for customer in existing}
        by_external_id = {customer.external_requester_id: customer for customer in existing}
        created = 0
        for record in records:
            customer = by_email.get(record.requester_email)
            if customer is None:
                customer = by_external_id.get(record.requester_id)
            if customer is None:
                customer = Customer(
                    external_requester_id=record.requester_id,
                    requester_name=record.requester_name,
                    requester_email=record.requester_email,
                )
                self._session.add(customer)
                created += 1
            else:
                customer.requester_name = record.requester_name
            by_email[record.requester_email] = customer
            by_external_id[record.requester_id] = customer
        await self._session.flush()
        return by_email, created

    async def _resolve_tags(
        self,
        records: list[TicketImportRecord],
    ) -> tuple[dict[str, Tag], int]:
        names = {tag for record in records for tag in record.tags}
        if not names:
            return {}, 0
        existing = (
            await self._session.execute(select(Tag).where(Tag.name.in_(names)))
        ).scalars().all()
        by_name = {tag.name: tag for tag in existing}
        created = 0
        for name in sorted(names):
            if name not in by_name:
                tag = Tag(name=name)
                self._session.add(tag)
                by_name[name] = tag
                created += 1
        await self._session.flush()
        return by_name, created

    async def _replace_tags(
        self,
        changed: list[tuple[Ticket, TicketImportRecord]],
        tags: dict[str, Tag],
    ) -> None:
        ticket_ids = [ticket.id for ticket, _ in changed]
        await self._session.execute(delete(TicketTag).where(TicketTag.ticket_id.in_(ticket_ids)))
        for ticket, record in changed:
            for tag_name in record.tags:
                self._session.add(TicketTag(ticket_id=ticket.id, tag_id=tags[tag_name].id))

    async def _replace_satisfaction(
        self,
        changed: list[tuple[Ticket, TicketImportRecord]],
    ) -> None:
        ticket_ids = [ticket.id for ticket, _ in changed]
        existing = (
            await self._session.execute(
                select(SatisfactionRating).where(SatisfactionRating.ticket_id.in_(ticket_ids))
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
    def _deduplicate(records: list[TicketImportRecord]) -> list[TicketImportRecord]:
        latest: dict[int, TicketImportRecord] = {}
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
