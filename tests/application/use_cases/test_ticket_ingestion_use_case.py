
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

from src.application.contracts.repositories import (
    CustomerRepository,
    SatisfactionRatingRepository,
    TagRepository,
    TicketRepository,
    TicketTagRepository,
)
from src.application.dtos.ingestion_control import IngestionControlState
from src.application.dtos.ticket_ingestion import (
    IngestTicketBatchInput,
    TicketSourceRecord,
)
from src.application.use_cases.ingestion_control import IngestTicketBatch
from src.domain.entities import (
    CustomerEntity,
    TagEntity,
    TicketPriority,
    TicketStatus,
)

CUSTOMER_ID = UUID("0198f17c-1a23-7000-8000-000000000101")
TICKET_ID = UUID("0198f17c-1a23-7000-8000-000000000102")
TAG_ID = UUID("0198f17c-1a23-7000-8000-000000000103")


def _record(*, email: str, ticket_id: int, requester_id: int) -> TicketSourceRecord:
    return TicketSourceRecord(
        ticket_id=ticket_id,
        subject="Falha de login",
        description="Erro ao autenticar",
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH,
        requester_id=requester_id,
        requester_name="Cliente",
        requester_email=email,
        assignee_id=91,
        assignee_name="Atendente",
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 1, 1, tzinfo=timezone.utc),
        first_response_at=datetime(2026, 7, 1, 0, 10, tzinfo=timezone.utc),
        tags=["login"],
    )


def test_ingestion_only_imports_registered_customers_and_batches_writes() -> None:
    asyncio.run(_run_ingestion())


async def _run_ingestion() -> None:
    customer = CustomerEntity(
        id=CUSTOMER_ID,
        requester_name="Cliente",
        requester_email="cliente@example.com",
        external_requester_id=None,
        is_monitored=True,
    )
    update_customers = AsyncMock()

    async def assign_ticket_ids(tickets):
        for ticket in tickets:
            ticket.id = TICKET_ID

    insert_many = AsyncMock(side_effect=assign_ticket_ids)
    complete_cycle = AsyncMock()
    replace_many = AsyncMock()
    synchronize_many = AsyncMock()

    customer_repository = cast(
        CustomerRepository,
        SimpleNamespace(
            find_monitored_by_emails=AsyncMock(
                return_value={"cliente@example.com": customer}
            ),
            update_many=update_customers,
        ),
    )
    ticket_repository = cast(
        TicketRepository,
        SimpleNamespace(
            get_ingestion_control=AsyncMock(
                return_value=IngestionControlState(
                    enabled=True,
                    worker_state="IDLE",
                    cursor_position=0,
                )
            ),
            get_by_external_ids=AsyncMock(return_value={}),
            insert_many=insert_many,
            update_many=AsyncMock(),
            complete_ingestion_cycle=complete_cycle,
        ),
    )
    tag_repository = cast(
        TagRepository,
        SimpleNamespace(
            resolve_by_names=AsyncMock(
                return_value={"login": TagEntity(id=TAG_ID, name="login")}
            )
        ),
    )
    ticket_tag_repository = cast(
        TicketTagRepository,
        SimpleNamespace(replace_many=replace_many),
    )
    satisfaction_repository = cast(
        SatisfactionRatingRepository,
        SimpleNamespace(synchronize_many=synchronize_many),
    )

    output = await IngestTicketBatch(
        customer_repository=customer_repository,
        ticket_repository=ticket_repository,
        tag_repository=tag_repository,
        ticket_tag_repository=ticket_tag_repository,
        satisfaction_repository=satisfaction_repository,
    ).execute(
        IngestTicketBatchInput(
            expected_cursor=0,
            source_total=2,
            records=[
                _record(
                    email="cliente@example.com",
                    ticket_id=1001,
                    requester_id=55,
                ),
                _record(
                    email="nao-cadastrado@example.com",
                    ticket_id=1002,
                    requester_id=56,
                ),
            ],
        )
    )

    assert output.received == 2
    assert output.matched_customers == 1
    assert output.ignored_unmonitored == 1
    assert output.tickets_created == 1
    assert output.next_cursor == 0
    assert customer.external_requester_id == 55
    update_customers.assert_awaited_once()
    insert_many.assert_awaited_once()
    replace_many.assert_awaited_once_with({TICKET_ID: [TAG_ID]})
    synchronize_many.assert_awaited_once_with({TICKET_ID: None})
    complete_cycle.assert_awaited_once_with(next_cursor=0)
