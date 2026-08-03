from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SatisfactionScore(str, Enum):
    GOOD = "GOOD"
    BAD = "BAD"
    UNOFFERED = "UNOFFERED"
    OFFERED = "OFFERED"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SOLVED = "SOLVED"
    NEW = "NEW"
    PENDING = "PENDING"
    HOLD = "HOLD"


class TicketPriority(str, Enum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class BaseEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserEntity(BaseEntity):
    email: str
    password_hash: bytes


class AuthSessionEntity(BaseEntity):
    user_id: UUID
    refresh_token_hash: bytes
    expires_at: datetime
    last_used_at: datetime
    revoked_at: datetime | None = None
    compromised_at: datetime | None = None
    rotation_counter: int = 0
    user_agent: str | None = None
    ip_address: str | None = None


class CustomerEntity(BaseEntity):
    external_requester_id: int | None = None
    requester_name: str
    requester_email: str
    is_monitored: bool = True


class TicketEntity(BaseEntity):
    customer_id: UUID
    external_ticket_id: int
    subject: str
    description: str
    first_response_at: datetime | None = None
    status: TicketStatus
    priority: TicketPriority
    assignee_external_id: int | None = None
    assignee_name: str | None = None
    source_created_at: datetime
    source_updated_at: datetime


class SatisfactionRatingEntity(BaseEntity):
    ticket_id: UUID
    score: SatisfactionScore
    offered_at: datetime | None = None
    rated_at: datetime | None = None
    comment: str = ""


class TagEntity(BaseEntity):
    name: str


class TicketTagEntity(BaseEntity):
    ticket_id: UUID
    tag_id: UUID
