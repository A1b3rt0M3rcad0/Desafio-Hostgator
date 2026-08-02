from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.ticket_ingestion import (
    BatchIngestionResult,
    TicketSourceRecord,
)
from src.infra.database.models import (
    Customer,
    SatisfactionRating,
    Tag,
    Ticket,
    TicketTag,
)


async def synchronize_ticket_batch(
    session: AsyncSession,
    records: list[TicketSourceRecord],
    *,
    invalid: int = 0,
    received: int | None = None,
) -> BatchIngestionResult:
    deduplicated = _deduplicate(records)
    customers, customers_created, customers_updated, conflicted = (
        await _upsert_customers(session, deduplicated)
    )

    matched = [
        (record, customers[record.requester_email])
        for record in deduplicated
        if record.requester_email in customers
    ]

    external_ids = [record.ticket_id for record, _ in matched]
    existing_tickets: list[Ticket] = []
    if external_ids:
        existing_tickets = (
            await session.execute(
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
        source_updated_at = _naive_utc(record.updated_at)
        if ticket is not None and ticket.source_updated_at >= source_updated_at:
            unchanged += 1
            continue

        values = {
            "customer_id": customer.id,
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
        if ticket is None:
            ticket = Ticket(external_ticket_id=record.ticket_id, **values)
            session.add(ticket)
            tickets_by_external_id[record.ticket_id] = ticket
            created += 1
        else:
            for key, value in values.items():
                setattr(ticket, key, value)
            updated += 1
        changed.append((ticket, record))

    await session.flush()
    if changed:
        tags = await _resolve_tags(session, changed)
        await _replace_tags(session, changed, tags)
        await _replace_satisfaction(session, changed)
        await session.flush()

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
    session: AsyncSession,
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
            await session.execute(
                select(Customer).where(
                    or_(
                        func.lower(Customer.requester_email).in_(emails),
                        Customer.external_requester_id.in_(external_ids),
                    )
                )
            )
        ).scalars().all()

    by_email = {
        customer.requester_email.strip().lower(): customer for customer in existing
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
            session.add(customer)
            by_email[email] = customer
            by_external_id[record.requester_id] = customer
            created += 1
        resolved[email] = customer

    await session.flush()
    return resolved, created, updated, conflicted


async def _resolve_tags(
    session: AsyncSession,
    changed: list[tuple[Ticket, TicketSourceRecord]],
) -> dict[str, Tag]:
    names = {name for _, record in changed for name in record.tags}
    if not names:
        return {}
    existing = (
        await session.execute(select(Tag).where(Tag.name.in_(names)))
    ).scalars().all()
    by_name = {tag.name: tag for tag in existing}
    for name in sorted(names):
        if name not in by_name:
            tag = Tag(name=name)
            session.add(tag)
            by_name[name] = tag
    await session.flush()
    return by_name


async def _replace_tags(
    session: AsyncSession,
    changed: list[tuple[Ticket, TicketSourceRecord]],
    tags: dict[str, Tag],
) -> None:
    ticket_ids = [ticket.id for ticket, _ in changed]
    await session.execute(
        delete(TicketTag).where(TicketTag.ticket_id.in_(ticket_ids))
    )
    for ticket, record in changed:
        for tag_name in record.tags:
            session.add(TicketTag(ticket_id=ticket.id, tag_id=tags[tag_name].id))


async def _replace_satisfaction(
    session: AsyncSession,
    changed: list[tuple[Ticket, TicketSourceRecord]],
) -> None:
    ticket_ids = [ticket.id for ticket, _ in changed]
    existing = (
        await session.execute(
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
                await session.delete(current)
            continue

        values = {
            "score": imported.score,
            "offered_at": _naive_utc(imported.offered_at),
            "rated_at": _naive_utc(imported.rated_at),
            "comment": imported.comment,
        }
        if current is None:
            session.add(SatisfactionRating(ticket_id=ticket.id, **values))
        else:
            for key, value in values.items():
                setattr(current, key, value)


def _deduplicate(records: list[TicketSourceRecord]) -> list[TicketSourceRecord]:
    latest: dict[int, TicketSourceRecord] = {}
    for record in records:
        current = latest.get(record.ticket_id)
        if current is None or record.updated_at >= current.updated_at:
            latest[record.ticket_id] = record
    return [latest[ticket_id] for ticket_id in sorted(latest)]


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
