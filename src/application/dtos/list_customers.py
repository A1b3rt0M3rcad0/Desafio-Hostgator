from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.application.dtos.cursor_page import CursorPage


class CustomerListItem(BaseModel):
    id: UUID
    external_requester_id: int
    requester_name: str
    requester_email: str
    created_at: datetime


class ListCustomersInput(BaseModel):
    cursor: str | None = None
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, max_length=200)

    @field_validator("search", mode="before")
    @classmethod
    def normalize_search(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = " ".join(str(value).split())
        return normalized or None


class ListCustomersOutput(BaseModel):
    page: CursorPage[CustomerListItem]
