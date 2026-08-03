from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid as SQLAlchemyUUID,
    func,
)
from sqlalchemy.dialects.mysql import BINARY as MySQLBinary
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

from src.domain.entities import SatisfactionScore, TicketPriority, TicketStatus

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IngestionControl(Base):
    __tablename__ = "ingestion_control"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(Integer(), primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False, server_default="0"
    )
    cursor_position: Mapped[int] = mapped_column(
        BigInteger(), nullable=False, default=0, server_default="0"
    )
    worker_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DISABLED", server_default="DISABLED"
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[bytes] = mapped_column(LargeBinary(255), nullable=False)
    auth_sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AuthSession(BaseModel):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint(
            "refresh_token_hash",
            name="uq_auth_sessions_refresh_token_hash",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    refresh_token_hash: Mapped[bytes] = mapped_column(MySQLBinary(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    compromised_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    rotation_counter: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user: Mapped[User] = relationship(back_populates="auth_sessions", lazy="joined")


class Customer(BaseModel):
    __tablename__ = "customers"

    external_requester_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True,
    )
    requester_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_monitored: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
    )
    tickets: Mapped[list[Ticket]] = relationship(
        back_populates="customer",
        lazy="selectin",
        passive_deletes=True,
    )


class Ticket(BaseModel):
    __tablename__ = "tickets"

    customer_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    external_ticket_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        SQLAlchemyEnum(TicketStatus, name="ticket_status", native_enum=True, validate_strings=True),
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SQLAlchemyEnum(TicketPriority, name="ticket_priority", native_enum=True, validate_strings=True),
        nullable=False,
    )
    assignee_external_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    assignee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    customer: Mapped[Customer] = relationship(back_populates="tickets", lazy="joined")
    satisfaction_rating: Mapped[SatisfactionRating | None] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
        lazy="selectin",
        passive_deletes=True,
    )
    tag_links: Mapped[list[TicketTag]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True,
    )
    tags: Mapped[list[Tag]] = relationship(
        secondary="ticket_tags",
        viewonly=True,
        lazy="selectin",
    )


class SatisfactionRating(BaseModel):
    __tablename__ = "satisfaction_ratings"

    ticket_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    score: Mapped[SatisfactionScore] = mapped_column(
        SQLAlchemyEnum(
            SatisfactionScore,
            name="satisfaction_score",
            native_enum=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    offered_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    rated_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    comment: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    ticket: Mapped[Ticket] = relationship(back_populates="satisfaction_rating", lazy="joined")


class Tag(BaseModel):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    ticket_links: Mapped[list[TicketTag]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True,
    )
    tickets: Mapped[list[Ticket]] = relationship(
        secondary="ticket_tags",
        viewonly=True,
        lazy="selectin",
    )


class TicketTag(BaseModel):
    __tablename__ = "ticket_tags"
    __table_args__ = (
        UniqueConstraint(
            "ticket_id",
            "tag_id",
            name="uq_ticket_tags_ticket_id_tag_id",
        ),
    )

    ticket_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tag_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    ticket: Mapped[Ticket] = relationship(back_populates="tag_links", lazy="joined")
    tag: Mapped[Tag] = relationship(back_populates="ticket_links", lazy="joined")
