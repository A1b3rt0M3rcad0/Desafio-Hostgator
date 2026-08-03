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

    def filters(self) -> AnalyticsFilters:
        return AnalyticsFilters.model_validate(
            self.model_dump(exclude={"top_topics_limit", "timeline_limit"})
        )


class CustomerMetricsInput(AnalyticsFilters):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    top_topics_limit: int = Field(default=1, ge=1, le=10)
    ticket_volume_min: int | None = Field(default=None, ge=0)
    ticket_volume_max: int | None = Field(default=None, ge=0)
    satisfaction_rate_min: float | None = Field(default=None, ge=0, le=1)
    satisfaction_rate_max: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_metric_ranges(self) -> "CustomerMetricsInput":
        if (
            self.ticket_volume_min is not None
            and self.ticket_volume_max is not None
            and self.ticket_volume_min > self.ticket_volume_max
        ):
            raise ValueError(
                "ticket_volume_min must be less than or equal to ticket_volume_max"
            )
        if (
            self.satisfaction_rate_min is not None
            and self.satisfaction_rate_max is not None
            and self.satisfaction_rate_min > self.satisfaction_rate_max
        ):
            raise ValueError(
                "satisfaction_rate_min must be less than or equal to satisfaction_rate_max"
            )
        return self


class StatusAggregate(BaseModel):
    label: str
    value: int


class PriorityAggregate(BaseModel):
    priority: str
    ticket_count: int
    resolved_tickets: int
    average_first_response_seconds: float | None = None


class TopicAggregate(BaseModel):
    tag: str
    ticket_count: int
    resolved_tickets: int
    average_first_response_seconds: float | None = None


class DashboardPeriodSnapshot(BaseModel):
    total_tickets: int
    resolved_tickets: int
    average_first_response_seconds: float | None = None
    responded_tickets: int
    good_ratings: int
    bad_ratings: int
    average_recurrence_seconds: float | None = None
    recurrence_sample_intervals: int
    customers_with_recurrence: int
    status_counts: list[StatusAggregate] = Field(default_factory=list)
    priority_aggregates: list[PriorityAggregate] = Field(default_factory=list)
    topic_aggregates: list[TopicAggregate] = Field(default_factory=list)


class TimelineAggregate(BaseModel):
    date: str
    opened: int
    resolved: int
    average_first_response_seconds: float | None = None
    good_ratings: int
    bad_ratings: int


class ResponseBucketAggregate(BaseModel):
    bucket: str
    ticket_count: int


class TopCustomerAggregate(BaseModel):
    customer_id: UUID
    requester_name: str
    requester_email: str
    ticket_count: int


class DashboardOperationalSnapshot(BaseModel):
    timeline: list[TimelineAggregate] = Field(default_factory=list)
    response_buckets: list[ResponseBucketAggregate] = Field(default_factory=list)
    unique_customers: int
    repeat_customers: int
    average_tickets_per_customer: float | None = None
    top_customers: list[TopCustomerAggregate] = Field(default_factory=list)


class TopicCount(BaseModel):
    tag: str
    ticket_count: int


class CustomerAnalyticsRow(BaseModel):
    customer_id: UUID
    external_requester_id: int
    requester_name: str
    requester_email: str
    ticket_volume: int
    resolved_tickets: int
    good_ratings: int
    bad_ratings: int
    average_first_response_seconds: float | None = None
    average_recurrence_seconds: float | None = None
    recurrence_sample_intervals: int
    top_topics: list[TopicCount] = Field(default_factory=list)


class CustomerAnalyticsQueryPage(BaseModel):
    items: list[CustomerAnalyticsRow]
    page: int
    page_size: int
    total: int
    has_next: bool
    has_previous: bool


class CustomerFilterOption(BaseModel):
    id: UUID
    requester_name: str
    requester_email: str


class TagFilterOption(BaseModel):
    id: UUID
    name: str


class AssigneeFilterOption(BaseModel):
    external_id: int
    name: str | None = None


class SatisfactionExportRecord(BaseModel):
    score: str
    offered_at: datetime | None = None
    rated_at: datetime | None = None
    comment: str


class ExportTicketRecord(BaseModel):
    internal_ticket_id: UUID
    ticket_id: int
    subject: str
    description: str
    status: str
    priority: str
    requester_id: int
    requester_name: str
    requester_email: str
    assignee_id: int | None = None
    assignee_name: str | None = None
    created_at: datetime
    updated_at: datetime
    first_response_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    satisfaction_rating: SatisfactionExportRecord | None = None


class MetricChange(BaseModel):
    change_percent: float | None = None
    change_points: float | None = None


class TicketVolumeMetric(MetricChange):
    value: int
    previous_value: int | None = None


class AverageRecurrenceMetric(MetricChange):
    average_seconds: float | None = None
    sample_intervals: int
    customers_with_recurrence: int
    previous_average_seconds: float | None = None


class ResolutionRateMetric(MetricChange):
    rate: float | None = None
    resolved: int
    total: int
    previous_rate: float | None = None


class SatisfactionRateMetric(MetricChange):
    rate: float | None = None
    good: int
    bad: int
    rated_total: int
    previous_rate: float | None = None


class AverageFirstResponseMetric(MetricChange):
    average_seconds: float | None = None
    responded_tickets: int
    unanswered_tickets: int
    previous_average_seconds: float | None = None


class DashboardMetricsOutput(BaseModel):
    ticket_volume: TicketVolumeMetric
    average_recurrence: AverageRecurrenceMetric
    resolution_rate: ResolutionRateMetric
    satisfaction_rate: SatisfactionRateMetric
    average_first_response: AverageFirstResponseMetric


class TicketsOverTimePoint(BaseModel):
    date: str
    value: int


class BasicDistributionPoint(BaseModel):
    label: str
    value: int


class DistributionPoint(BasicDistributionPoint):
    previous_value: int | None = None
    change_percent: float | None = None


class OperationTimeseriesPoint(BaseModel):
    date: str
    opened: int
    resolved: int
    resolution_rate: float | None = None
    average_first_response_seconds: float | None = None
    satisfaction_rate: float | None = None
    rated_tickets: int


class PriorityBreakdownPoint(BaseModel):
    priority: str
    ticket_count: int
    share: float | None = None
    resolved_tickets: int
    resolution_rate: float | None = None
    average_first_response_seconds: float | None = None
    previous_ticket_count: int | None = None
    change_percent: float | None = None


class FirstResponseDistributionPoint(BaseModel):
    bucket: str
    label: str
    ticket_count: int
    share: float | None = None


class TopicBreakdownPoint(BaseModel):
    tag: str
    ticket_count: int
    share: float | None = None
    resolved_tickets: int
    resolution_rate: float | None = None
    average_first_response_seconds: float | None = None
    rank: int
    previous_ticket_count: int | None = None
    change_percent: float | None = None


class DashboardChartsOutput(BaseModel):
    tickets_over_time: list[TicketsOverTimePoint]
    status_distribution: list[DistributionPoint]
    priority_distribution: list[BasicDistributionPoint]
    operation_timeseries: list[OperationTimeseriesPoint]
    priority_breakdown: list[PriorityBreakdownPoint]
    first_response_distribution: list[FirstResponseDistributionPoint]
    top_topics: list[TopicBreakdownPoint]


class TopCustomerOutput(BaseModel):
    customer_id: UUID
    requester_name: str
    requester_email: str
    ticket_count: int


class CustomerBehaviorOutput(BaseModel):
    unique_customers: int
    repeat_customers: int
    repeat_customer_rate: float | None = None
    average_tickets_per_customer: float | None = None
    top_customers: list[TopCustomerOutput]


class DashboardScopeOutput(BaseModel):
    from_at: datetime | None = None
    to_at: datetime | None = None
    previous_from_at: datetime | None = None
    previous_to_at: datetime | None = None
    is_comparable: bool
    timezone: str = "UTC"


class DashboardTopDriver(BaseModel):
    label: str
    ticket_count: int
    share: float | None = None
    change_percent: float | None = None


class DashboardSummaryOutput(BaseModel):
    headline: str
    primary_alert: str
    primary_improvement: str
    top_driver: DashboardTopDriver | None = None


class DashboardFilterOptionsOutput(BaseModel):
    tags: list[dict[str, Any]]
    customers: list[dict[str, Any]]
    assignees: list[dict[str, Any]]


class DashboardOutput(BaseModel):
    filters: dict[str, Any]
    metrics: DashboardMetricsOutput
    charts: DashboardChartsOutput
    customer_behavior: CustomerBehaviorOutput
    scope: DashboardScopeOutput
    summary: DashboardSummaryOutput
    filter_options: DashboardFilterOptionsOutput
    generated_at: datetime


class CustomerMetricsItem(BaseModel):
    customer_id: UUID
    external_requester_id: int
    requester_name: str
    requester_email: str
    ticket_volume: int
    average_recurrence_seconds: float | None = None
    recurrence_sample_intervals: int
    resolution_rate: float | None = None
    resolved_tickets: int
    satisfaction_rate: float | None = None
    good_ratings: int
    bad_ratings: int
    average_first_response_seconds: float | None = None
    top_topics: list[TopicCount]


class CustomerMetricsPage(BaseModel):
    items: list[CustomerMetricsItem]
    page: int
    page_size: int
    total: int
    has_next: bool
    has_previous: bool
