from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.domain.entities import SatisfactionScore, TicketPriority, TicketStatus
from src.infra.database.models import Customer, SatisfactionRating, Tag, Ticket, TicketTag
from src.infra.database.unit_of_work import UnitOfWork


def _datetime(value: str | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


async def seed_analytics_dataset(
    unit_of_work: UnitOfWork,
    records: list[dict[str, Any]],
) -> None:
    session = unit_of_work.session
    customers: dict[str, Customer] = {}
    tags: dict[str, Tag] = {}

    for record in records:
        email = str(record["requester_email"]).lower()
        customer = customers.get(email)
        if customer is None:
            customer = Customer(
                external_requester_id=int(record["requester_id"]),
                requester_name=str(record["requester_name"]),
                requester_email=email,
            )
            session.add(customer)
            customers[email] = customer

        for tag_name in record.get("tags", []):
            if tag_name not in tags:
                tag = Tag(name=tag_name)
                session.add(tag)
                tags[tag_name] = tag

    await session.flush()

    for record in records:
        customer = customers[str(record["requester_email"]).lower()]
        ticket = Ticket(
            customer_id=customer.id,
            external_ticket_id=int(record["ticket_id"]),
            subject=str(record.get("subject") or f'Ticket {record["ticket_id"]}'),
            description=str(record.get("description") or "Registro de teste"),
            first_response_at=_datetime(record.get("first_response_at")),
            status=TicketStatus(str(record["status"]).upper()),
            priority=TicketPriority(str(record.get("priority", "NORMAL")).upper()),
            assignee_external_id=record.get("assignee_id"),
            assignee_name=record.get("assignee_name"),
            source_created_at=_datetime(record["created_at"]),
            source_updated_at=_datetime(record.get("updated_at") or record["created_at"]),
        )
        session.add(ticket)
        await session.flush()

        for tag_name in record.get("tags", []):
            session.add(TicketTag(ticket_id=ticket.id, tag_id=tags[tag_name].id))

        rating = record.get("satisfaction_rating")
        if rating:
            session.add(
                SatisfactionRating(
                    ticket_id=ticket.id,
                    score=SatisfactionScore(str(rating["score"]).upper()),
                    offered_at=_datetime(rating.get("offered_at")),
                    rated_at=_datetime(rating.get("rated_at")),
                    comment=str(rating.get("comment") or ""),
                )
            )

    await session.flush()
