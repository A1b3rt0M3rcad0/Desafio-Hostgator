from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import TicketPriority, TicketStatus


class TicketListItem(BaseModel):
    id: UUID
    external_ticket_id: int
    subject: str
    status: TicketStatus
    priority: TicketPriority
    assignee_name: str | None = None
    source_created_at: datetime
    source_updated_at: datetime


class ListTicketsInput(BaseModel):
    cursor: str | None = None
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, max_length=200)
    statuses: list[TicketStatus] = Field(default_factory=list)
    priorities: list[TicketPriority] = Field(default_factory=list)
    from_at: datetime | None = None
    to_at: datetime | None = None

    @field_validator("search", mode="before")
    @classmethod
    def normalize_search(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = " ".join(str(value).split())
        return normalized or None

    @field_validator("statuses", "priorities", mode="before")
    @classmethod
    def normalize_lists(cls, value: Any, info: ValidationInfo) -> Any:
        del info
        if value is None or value == "":
            return []
        items = (
            [item.strip() for item in value.split(",") if item.strip()]
            if isinstance(value, str)
            else value
        )
        return [item.upper() if isinstance(item, str) else item for item in items]

    @model_validator(mode="after")
    def validate_period(self) -> "ListTicketsInput":
        if self.from_at and self.to_at and self.from_at > self.to_at:
            raise ValueError("from_at must be earlier than or equal to to_at")
        return self


class ListTicketsOutput(BaseModel):
    page: CursorPage[TicketListItem]
