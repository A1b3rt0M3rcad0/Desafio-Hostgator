from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from src.domain.entities import SatisfactionScore, TicketPriority, TicketStatus


class AnalyticsFilters(BaseModel):
    from_at: datetime | None = None
    to_at: datetime | None = None
    customer_ids: list[UUID] = Field(default_factory=list)
    requester_emails: list[str] = Field(default_factory=list)
    statuses: list[TicketStatus] = Field(default_factory=list)
    priorities: list[TicketPriority] = Field(default_factory=list)
    tag_ids: list[UUID] = Field(default_factory=list)
    tag_names: list[str] = Field(default_factory=list)
    assignee_external_ids: list[int] = Field(default_factory=list)
    satisfaction_scores: list[SatisfactionScore] = Field(default_factory=list)
    has_first_response: bool | None = None

    @field_validator(
        "customer_ids",
        "requester_emails",
        "statuses",
        "priorities",
        "tag_ids",
        "tag_names",
        "assignee_external_ids",
        "satisfaction_scores",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value: Any, info: ValidationInfo) -> Any:
        if value is None or value == "":
            items: Any = []
        elif isinstance(value, str):
            items = [item.strip() for item in value.split(",") if item.strip()]
        else:
            items = value
        if info.field_name in {"statuses", "priorities", "satisfaction_scores"}:
            return [item.upper() if isinstance(item, str) else item for item in items]
        return items

    @field_validator("requester_emails", mode="after")
    @classmethod
    def normalize_emails(cls, value: list[str]) -> list[str]:
        return sorted({email.strip().lower() for email in value if email.strip()})

    @field_validator("tag_names", mode="after")
    @classmethod
    def normalize_tag_names(cls, value: list[str]) -> list[str]:
        return sorted({name.strip() for name in value if name.strip()})

    @model_validator(mode="after")
    def validate_period(self) -> "AnalyticsFilters":
        if self.from_at and self.to_at and self.from_at > self.to_at:
            raise ValueError("from_at must be earlier than or equal to to_at")
        return self


class DashboardInput(AnalyticsFilters):
    top_topics_limit: int = Field(default=10, ge=1, le=50)
    timeline_limit: int = Field(default=90, ge=1, le=366)


class CustomerMetricsInput(AnalyticsFilters):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    top_topics_limit: int = Field(default=1, ge=1, le=10)


class CustomerMetricsPage(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    has_next: bool
    has_previous: bool
