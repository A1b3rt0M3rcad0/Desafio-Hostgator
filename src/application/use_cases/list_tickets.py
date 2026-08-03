from base64 import urlsafe_b64encode
from datetime import datetime, timezone

from src.application.contracts.repositories import TicketRepository
from src.application.contracts.use_cases import ListTickets as ListTicketsContract
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.list_tickets import ListTicketsInput, ListTicketsOutput
from src.domain.entities import TicketEntity


_REPOSITORY_BATCH_SIZE = 100


class ListTickets(ListTicketsContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: ListTicketsInput) -> ListTicketsOutput:
        items: list[TicketEntity] = []
        scan_cursor = input_dto.cursor
        has_next = False

        while True:
            source_page = await self._repository.page(
                scan_cursor,
                _REPOSITORY_BATCH_SIZE,
            )
            for ticket in source_page.items:
                if not self._matches(ticket, input_dto):
                    continue
                if len(items) == input_dto.page_size:
                    has_next = True
                    break
                items.append(ticket)

            if has_next or not source_page.has_next or not source_page.next_cursor:
                break
            scan_cursor = source_page.next_cursor

        next_cursor = (
            self._cursor_for(items[-1])
            if has_next and items
            else None
        )
        return ListTicketsOutput(
            page=CursorPage[TicketEntity](
                items=items,
                next_cursor=next_cursor,
                previous_cursor=None,
                has_next=has_next,
                has_previous=input_dto.cursor is not None,
            )
        )

    @classmethod
    def _matches(
        cls,
        ticket: TicketEntity,
        filters: ListTicketsInput,
    ) -> bool:
        if filters.statuses and ticket.status not in filters.statuses:
            return False
        if filters.priorities and ticket.priority not in filters.priorities:
            return False

        created_at = cls._naive_utc(ticket.source_created_at)
        from_at = cls._naive_utc(filters.from_at)
        to_at = cls._naive_utc(filters.to_at)
        if from_at is not None and created_at < from_at:
            return False
        if to_at is not None and created_at > to_at:
            return False
        return True

    @staticmethod
    def _naive_utc(value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _cursor_for(ticket: TicketEntity) -> str | None:
        if ticket.id is None:
            return None
        return urlsafe_b64encode(str(ticket.id).encode()).decode()
