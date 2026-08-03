from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import TicketEntity, TicketPriority, TicketStatus


class ListTicketsInput(BaseModel):
    cursor: str | None = None
    page_size: int = Field(default=20, ge=1, le=100)
    statuses: list[TicketStatus] = Field(default_factory=list)
    priorities: list[TicketPriority] = Field(default_factory=list)
    from_at: datetime | None = None
    to_at: datetime | None = None

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
    page: CursorPage[TicketEntity]
