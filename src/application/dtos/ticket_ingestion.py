from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.domain.entities import (
    CustomerEntity,
    SatisfactionScore,
    TicketEntity,
    TicketPriority,
    TicketStatus,
)


class SatisfactionSourceRecord(BaseModel):
    score: SatisfactionScore
    offered_at: datetime | None = None
    rated_at: datetime | None = None
    comment: str = ""

    @field_validator("score", mode="before")
    @classmethod
    def normalize_score(cls, value: Any) -> Any:
        return str(value).upper() if value is not None else value


class TicketSourceRecord(BaseModel):
    ticket_id: int
    subject: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    status: TicketStatus
    priority: TicketPriority
    requester_id: int
    requester_name: str = Field(min_length=1, max_length=255)
    requester_email: str = Field(min_length=3, max_length=255)
    assignee_id: int | None = None
    assignee_name: str | None = Field(default=None, max_length=255)
    created_at: datetime
    updated_at: datetime
    first_response_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    satisfaction_rating: SatisfactionSourceRecord | None = None

    @field_validator("status", "priority", mode="before")
    @classmethod
    def normalize_enum(cls, value: Any) -> Any:
        return str(value).upper() if value is not None else value

    @field_validator("requester_email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return sorted({item.strip() for item in value if item and item.strip()})


class CustomerSourceResult(BaseModel):
    customer: CustomerEntity
    created: bool = False


class TicketSourceResult(BaseModel):
    ticket: TicketEntity
    created: bool = False
    unchanged: bool = False
