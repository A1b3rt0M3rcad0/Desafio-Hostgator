
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from src.application.contracts.ingestion_control import (
    GetIngestionControl as GetIngestionControlContract,
    IngestTicketBatch as IngestTicketBatchContract,
    UpdateIngestionControl as UpdateIngestionControlContract,
)
from src.application.contracts.repositories import (
    CustomerRepository,
    SatisfactionRatingRepository,
    TagRepository,
    TicketRepository,
    TicketTagRepository,
)
from src.application.dtos.ingestion_control import (
    GetIngestionControlOutput,
    UpdateIngestionControlInput,
    UpdateIngestionControlOutput,
)
from src.application.dtos.ticket_ingestion import (
    IngestTicketBatchInput,
    IngestTicketBatchOutput,
    TicketSourceRecord,
)
from src.domain.entities import CustomerEntity, TicketEntity


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class GetIngestionControl(GetIngestionControlContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self) -> GetIngestionControlOutput:
        control = await self._repository.get_ingestion_control()
        return GetIngestionControlOutput(control=control)


class UpdateIngestionControl(UpdateIngestionControlContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        input_dto: UpdateIngestionControlInput,
    ) -> UpdateIngestionControlOutput:
        control = await self._repository.set_ingestion_enabled(input_dto.enabled)
        return UpdateIngestionControlOutput(control=control)


class IngestTicketBatch(IngestTicketBatchContract):
    def __init__(
        self,
        customer_repository: CustomerRepository,
        ticket_repository: TicketRepository,
        tag_repository: TagRepository,
        ticket_tag_repository: TicketTagRepository,
        satisfaction_repository: SatisfactionRatingRepository,
    ) -> None:
        self._customers = customer_repository
        self._tickets = ticket_repository
        self._tags = tag_repository
        self._ticket_tags = ticket_tag_repository
        self._ratings = satisfaction_repository

    async def execute(
        self,
        input_dto: IngestTicketBatchInput,
    ) -> IngestTicketBatchOutput:
        control = await self._tickets.get_ingestion_control(for_update=True)
        if not control.enabled:
            return IngestTicketBatchOutput(
                received=0,
                matched_customers=0,
                ignored_unmonitored=0,
                identity_conflicts=0,
                tickets_created=0,
                tickets_updated=0,
                tickets_unchanged=0,
                next_cursor=control.cursor_position,
            )
        if control.cursor_position != input_dto.expected_cursor:
            raise RuntimeError(
                "Ingestion cursor changed while the batch was being prepared"
            )

        records_by_ticket_id: dict[int, TicketSourceRecord] = {}
        for record in input_dto.records:
            if record.ticket_id in records_by_ticket_id:
                raise ValueError(
                    f"Duplicate ticket_id in source batch: {record.ticket_id}"
                )
            records_by_ticket_id[record.ticket_id] = record

        records = list(records_by_ticket_id.values())
        emails = {record.requester_email for record in records}
        customers_by_email = await self._customers.find_monitored_by_emails(
            emails
        )

        customer_updates: dict[UUID, CustomerEntity] = {}
        matched_records: list[tuple[TicketSourceRecord, CustomerEntity]] = []
        matched_customer_ids: set[UUID] = set()
        ignored_unmonitored = 0
        identity_conflicts = 0

        for record in records:
            customer = customers_by_email.get(record.requester_email)
            if customer is None:
                ignored_unmonitored += 1
                continue
            if customer.id is None:
                raise RuntimeError("Persisted customer does not have an ID")
            if customer.external_requester_id is None:
                customer.external_requester_id = record.requester_id
                customer_updates[customer.id] = customer
            elif customer.external_requester_id != record.requester_id:
                identity_conflicts += 1
                continue
            matched_records.append((record, customer))
            matched_customer_ids.add(customer.id)

        if customer_updates:
            await self._customers.update_many(list(customer_updates.values()))

        external_ticket_ids = {
            record.ticket_id for record, _ in matched_records
        }
        existing_by_external_id = await self._tickets.get_by_external_ids(
            external_ticket_ids
        )

        new_tickets: list[TicketEntity] = []
        updated_tickets: list[TicketEntity] = []
        changed: list[tuple[TicketSourceRecord, TicketEntity]] = []
        unchanged = 0

        for record, customer in matched_records:
            assert customer.id is not None
            existing = existing_by_external_id.get(record.ticket_id)
            source_updated_at = _naive_utc(record.updated_at)
            assert source_updated_at is not None
            if existing is not None:
                if existing.customer_id != customer.id:
                    identity_conflicts += 1
                    continue
                if existing.source_updated_at >= source_updated_at:
                    unchanged += 1
                    continue
                self._apply_source(existing, record, customer.id)
                updated_tickets.append(existing)
                changed.append((record, existing))
                continue

            ticket = TicketEntity(
                customer_id=customer.id,
                external_ticket_id=record.ticket_id,
                subject=record.subject,
                description=record.description,
                first_response_at=_naive_utc(record.first_response_at),
                status=record.status,
                priority=record.priority,
                assignee_external_id=record.assignee_id,
                assignee_name=record.assignee_name,
                source_created_at=_required_datetime(record.created_at),
                source_updated_at=source_updated_at,
            )
            new_tickets.append(ticket)
            changed.append((record, ticket))

        if new_tickets:
            await self._tickets.insert_many(new_tickets)
        if updated_tickets:
            await self._tickets.update_many(updated_tickets)

        all_tag_names = sorted(
            {
                tag_name
                for record, _ in changed
                for tag_name in record.tags
            }
        )
        tags_by_name = await self._tags.resolve_by_names(all_tag_names)

        tags_by_ticket: dict[UUID, list[UUID]] = {}
        ratings_by_ticket = {}
        for record, ticket in changed:
            if ticket.id is None:
                raise RuntimeError("Ticket ID was not generated during batch insert")
            tags_by_ticket[ticket.id] = [
                tag.id
                for name in record.tags
                if (tag := tags_by_name.get(name)) is not None
                and tag.id is not None
            ]
            ratings_by_ticket[ticket.id] = record.satisfaction_rating

        if tags_by_ticket:
            await self._ticket_tags.replace_many(tags_by_ticket)
            await self._ratings.synchronize_many(ratings_by_ticket)

        next_cursor = (
            input_dto.expected_cursor + len(input_dto.records)
        ) % input_dto.source_total
        await self._tickets.complete_ingestion_cycle(next_cursor=next_cursor)

        return IngestTicketBatchOutput(
            received=len(input_dto.records),
            matched_customers=len(matched_customer_ids),
            ignored_unmonitored=ignored_unmonitored,
            identity_conflicts=identity_conflicts,
            tickets_created=len(new_tickets),
            tickets_updated=len(updated_tickets),
            tickets_unchanged=unchanged,
            next_cursor=next_cursor,
        )

    @staticmethod
    def _apply_source(
        ticket: TicketEntity,
        record: TicketSourceRecord,
        customer_id: UUID,
    ) -> None:
        ticket.customer_id = customer_id
        ticket.subject = record.subject
        ticket.description = record.description
        ticket.first_response_at = _naive_utc(record.first_response_at)
        ticket.status = record.status
        ticket.priority = record.priority
        ticket.assignee_external_id = record.assignee_id
        ticket.assignee_name = record.assignee_name
        ticket.source_created_at = _required_datetime(record.created_at)
        ticket.source_updated_at = _required_datetime(record.updated_at)


def _required_datetime(value: datetime) -> datetime:
    normalized = _naive_utc(value)
    assert normalized is not None
    return normalized
