from __future__ import annotations

from enum import Enum


class MetricCode(str, Enum):
    TICKET_VOLUME = "ticket_volume"
    AVERAGE_RECURRENCE_SECONDS = "average_recurrence_seconds"
    TOP_TOPICS = "top_topics"
    RESOLUTION_RATE = "resolution_rate"
    SATISFACTION_RATE = "satisfaction_rate"
    AVERAGE_FIRST_RESPONSE_SECONDS = "average_first_response_seconds"


class ReportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


class ReportScope(str, Enum):
    OVERALL = "overall"
    CUSTOMER = "customer"


class DataExportField(str, Enum):
    TICKET_ID = "ticket_id"
    SUBJECT = "subject"
    DESCRIPTION = "description"
    STATUS = "status"
    PRIORITY = "priority"
    REQUESTER_ID = "requester_id"
    REQUESTER_NAME = "requester_name"
    REQUESTER_EMAIL = "requester_email"
    ASSIGNEE_ID = "assignee_id"
    ASSIGNEE_NAME = "assignee_name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    FIRST_RESPONSE_AT = "first_response_at"
    TAGS = "tags"
    SATISFACTION_RATING = "satisfaction_rating"


DEFAULT_DATA_EXPORT_FIELDS: tuple[DataExportField, ...] = tuple(DataExportField)
DEFAULT_METRICS: tuple[MetricCode, ...] = tuple(MetricCode)
RESOLVED_STATUSES: tuple[str, ...] = ("SOLVED", "CLOSED")
RATED_SATISFACTION_SCORES: tuple[str, ...] = ("GOOD", "BAD")
