from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.application.dtos.analytics import AnalyticsFilters
from src.domain.analytics import (
    DEFAULT_DATA_EXPORT_FIELDS,
    DEFAULT_METRICS,
    DataExportField,
    MetricCode,
    ReportFormat,
    ReportScope,
)


class DataExportPreviewInput(BaseModel):
    filters: AnalyticsFilters = Field(default_factory=AnalyticsFilters)
    fields: list[DataExportField] = Field(default_factory=lambda: list(DEFAULT_DATA_EXPORT_FIELDS))
    limit: int = Field(default=50, ge=1, le=100)

    @field_validator("fields", mode="before")
    @classmethod
    def normalize_fields(cls, value: Any) -> Any:
        if value is None or value == []:
            return list(DEFAULT_DATA_EXPORT_FIELDS)
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class DataExportInput(BaseModel):
    format: ReportFormat
    filters: AnalyticsFilters = Field(default_factory=AnalyticsFilters)
    fields: list[DataExportField] = Field(default_factory=lambda: list(DEFAULT_DATA_EXPORT_FIELDS))

    @field_validator("fields", mode="before")
    @classmethod
    def normalize_fields(cls, value: Any) -> Any:
        if value is None or value == []:
            return list(DEFAULT_DATA_EXPORT_FIELDS)
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class MetricsExportInput(BaseModel):
    format: ReportFormat
    scope: ReportScope = ReportScope.OVERALL
    metrics: list[MetricCode] = Field(default_factory=lambda: list(DEFAULT_METRICS))
    filters: AnalyticsFilters = Field(default_factory=AnalyticsFilters)
    top_topics_limit: int = Field(default=10, ge=1, le=50)

    @field_validator("metrics", mode="before")
    @classmethod
    def normalize_metrics(cls, value: Any) -> Any:
        if value is None or value == []:
            return list(DEFAULT_METRICS)
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class ExportedFile(BaseModel):
    filename: str
    media_type: str
    content: bytes

    model_config = {"arbitrary_types_allowed": True}


class DataExportPreviewOutput(BaseModel):
    total_matching: int
    preview_count: int
    fields: list[str]
    items: list[dict[str, Any]]
