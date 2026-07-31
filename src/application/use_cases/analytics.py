from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.application.contracts.analytics import AnalyticsQueryRepository, ReportWriterFactory
from src.application.dtos.analytics import (
    CustomerMetricsInput,
    CustomerMetricsPage,
    DashboardInput,
    ExportedFile,
    MetricExportInput,
    RawExportInput,
    RawPreviewInput,
    RawPreviewOutput,
)
from src.domain.analytics import DEFAULT_METRICS, DEFAULT_RAW_FIELDS, MetricCode, ReportFormat, ReportScope


_MEDIA_TYPES = {
    ReportFormat.CSV: "text/csv; charset=utf-8",
    ReportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class GetDashboardOverview:
    def __init__(self, repository: AnalyticsQueryRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DashboardInput) -> dict[str, Any]:
        return await self._repository.get_dashboard(
            input_dto,
            input_dto.top_topics_limit,
            input_dto.timeline_limit,
        )


class ListCustomerMetrics:
    def __init__(self, repository: AnalyticsQueryRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: CustomerMetricsInput) -> CustomerMetricsPage:
        result = await self._repository.list_customer_metrics(input_dto)
        return CustomerMetricsPage(**result)


class GetReportCatalog:
    async def execute(self) -> dict[str, Any]:
        return {
            "formats": [
                {
                    "code": ReportFormat.CSV.value,
                    "label": "CSV",
                    "media_type": _MEDIA_TYPES[ReportFormat.CSV],
                },
                {
                    "code": ReportFormat.XLSX.value,
                    "label": "Excel (.xlsx)",
                    "media_type": _MEDIA_TYPES[ReportFormat.XLSX],
                },
            ],
            "metrics": [
                {"code": MetricCode.TICKET_VOLUME.value, "label": "Volume de tickets", "unit": "tickets"},
                {"code": MetricCode.AVERAGE_RECURRENCE_SECONDS.value, "label": "Frequência média", "unit": "seconds"},
                {"code": MetricCode.TOP_TOPICS.value, "label": "Assuntos principais", "unit": "tickets"},
                {"code": MetricCode.RESOLUTION_RATE.value, "label": "Taxa de resolução", "unit": "ratio"},
                {"code": MetricCode.SATISFACTION_RATE.value, "label": "Índice de satisfação", "unit": "ratio"},
                {"code": MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS.value, "label": "Tempo médio até a primeira resposta", "unit": "seconds"},
            ],
            "raw_fields": [
                {"code": field.value, "label": field.value.replace("_", " ").title()}
                for field in DEFAULT_RAW_FIELDS
            ],
            "presets": [
                {
                    "code": "mock_complete",
                    "label": "Contrato completo do mock",
                    "fields": [field.value for field in DEFAULT_RAW_FIELDS],
                }
            ],
            "scopes": [scope.value for scope in ReportScope],
        }


class PreviewRawReport:
    def __init__(self, repository: AnalyticsQueryRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: RawPreviewInput) -> RawPreviewOutput:
        total = await self._repository.count_raw_rows(input_dto.filters)
        rows = await self._repository.fetch_raw_rows(
            input_dto.filters,
            input_dto.fields,
            input_dto.limit,
            0,
        )
        return RawPreviewOutput(
            total_matching=total,
            preview_count=len(rows),
            fields=[field.value for field in input_dto.fields],
            items=rows,
        )


class ExportRawReport:
    def __init__(
        self,
        repository: AnalyticsQueryRepository,
        writer_factory: ReportWriterFactory,
        batch_size: int = 1000,
    ) -> None:
        self._repository = repository
        self._writer_factory = writer_factory
        self._batch_size = batch_size

    async def execute(self, input_dto: RawExportInput) -> ExportedFile:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            batch = await self._repository.fetch_raw_rows(
                input_dto.filters,
                input_dto.fields,
                self._batch_size,
                offset,
            )
            rows.extend(batch)
            if len(batch) < self._batch_size:
                break
            offset += len(batch)
        columns = [field.value for field in input_dto.fields]
        writer = self._writer_factory.create(input_dto.format)
        content = writer.write(rows, columns, "RAW")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return ExportedFile(
            filename=f"tickets-raw-{timestamp}.{input_dto.format.value}",
            media_type=_MEDIA_TYPES[input_dto.format],
            content=content,
        )


class ExportMetricsReport:
    def __init__(
        self,
        repository: AnalyticsQueryRepository,
        writer_factory: ReportWriterFactory,
    ) -> None:
        self._repository = repository
        self._writer_factory = writer_factory

    async def execute(self, input_dto: MetricExportInput) -> ExportedFile:
        metrics = input_dto.metrics or list(DEFAULT_METRICS)
        if input_dto.scope == ReportScope.OVERALL:
            rows = await self._overall_rows(input_dto, metrics)
        else:
            rows = await self._customer_rows(input_dto, metrics)
        columns = [
            "scope_type",
            "scope_id",
            "scope_label",
            "metric_code",
            "metric_label",
            "value",
            "unit",
            "numerator",
            "denominator",
            "sample_size",
            "dimension",
            "rank",
            "period_start",
            "period_end",
        ]
        writer = self._writer_factory.create(input_dto.format)
        content = writer.write(rows, columns, "Metricas")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return ExportedFile(
            filename=f"metricas-{input_dto.scope.value}-{timestamp}.{input_dto.format.value}",
            media_type=_MEDIA_TYPES[input_dto.format],
            content=content,
        )

    async def _overall_rows(
        self,
        input_dto: MetricExportInput,
        metrics: list[MetricCode],
    ) -> list[dict[str, Any]]:
        dashboard = await self._repository.get_dashboard(
            input_dto.filters,
            input_dto.top_topics_limit,
            1,
        )
        values = dashboard["metrics"]
        period = self._period(input_dto)
        rows: list[dict[str, Any]] = []
        if MetricCode.TICKET_VOLUME in metrics:
            rows.append(self._metric_row("overall", "all", "Visão geral", MetricCode.TICKET_VOLUME, "Volume de tickets", values["ticket_volume"]["value"], "tickets", period=period))
        if MetricCode.AVERAGE_RECURRENCE_SECONDS in metrics:
            recurrence = values["average_recurrence"]
            rows.append(self._metric_row("overall", "all", "Visão geral", MetricCode.AVERAGE_RECURRENCE_SECONDS, "Frequência média", recurrence["average_seconds"], "seconds", sample_size=recurrence["sample_intervals"], period=period))
        if MetricCode.RESOLUTION_RATE in metrics:
            resolution = values["resolution_rate"]
            rows.append(self._metric_row("overall", "all", "Visão geral", MetricCode.RESOLUTION_RATE, "Taxa de resolução", resolution["rate"], "ratio", numerator=resolution["resolved"], denominator=resolution["total"], period=period))
        if MetricCode.SATISFACTION_RATE in metrics:
            satisfaction = values["satisfaction_rate"]
            rows.append(self._metric_row("overall", "all", "Visão geral", MetricCode.SATISFACTION_RATE, "Índice de satisfação", satisfaction["rate"], "ratio", numerator=satisfaction["good"], denominator=satisfaction["rated_total"], sample_size=satisfaction["rated_total"], period=period))
        if MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS in metrics:
            response = values["average_first_response"]
            rows.append(self._metric_row("overall", "all", "Visão geral", MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS, "Tempo médio até a primeira resposta", response["average_seconds"], "seconds", sample_size=response["responded_tickets"], period=period))
        if MetricCode.TOP_TOPICS in metrics:
            for topic in dashboard["charts"]["top_topics"]:
                rows.append(self._metric_row("overall", "all", "Visão geral", MetricCode.TOP_TOPICS, "Assuntos principais", topic["ticket_count"], "tickets", dimension=topic["tag"], rank=topic["rank"], period=period))
        return rows

    async def _customer_rows(
        self,
        input_dto: MetricExportInput,
        metrics: list[MetricCode],
    ) -> list[dict[str, Any]]:
        page = 1
        rows: list[dict[str, Any]] = []
        period = self._period(input_dto)
        while True:
            page_input = CustomerMetricsInput(
                **input_dto.filters.model_dump(),
                page=page,
                page_size=100,
                top_topics_limit=input_dto.top_topics_limit,
            )
            result = await self._repository.list_customer_metrics(page_input)
            for customer in result["items"]:
                scope_id = customer["customer_id"]
                scope_label = f'{customer["requester_name"]} <{customer["requester_email"]}>'
                if MetricCode.TICKET_VOLUME in metrics:
                    rows.append(self._metric_row("customer", scope_id, scope_label, MetricCode.TICKET_VOLUME, "Volume de tickets", customer["ticket_volume"], "tickets", period=period))
                if MetricCode.AVERAGE_RECURRENCE_SECONDS in metrics:
                    rows.append(self._metric_row("customer", scope_id, scope_label, MetricCode.AVERAGE_RECURRENCE_SECONDS, "Frequência média", customer["average_recurrence_seconds"], "seconds", sample_size=customer["recurrence_sample_intervals"], period=period))
                if MetricCode.RESOLUTION_RATE in metrics:
                    rows.append(self._metric_row("customer", scope_id, scope_label, MetricCode.RESOLUTION_RATE, "Taxa de resolução", customer["resolution_rate"], "ratio", numerator=customer["resolved_tickets"], denominator=customer["ticket_volume"], period=period))
                if MetricCode.SATISFACTION_RATE in metrics:
                    rated_total = customer["good_ratings"] + customer["bad_ratings"]
                    rows.append(self._metric_row("customer", scope_id, scope_label, MetricCode.SATISFACTION_RATE, "Índice de satisfação", customer["satisfaction_rate"], "ratio", numerator=customer["good_ratings"], denominator=rated_total, sample_size=rated_total, period=period))
                if MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS in metrics:
                    rows.append(self._metric_row("customer", scope_id, scope_label, MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS, "Tempo médio até a primeira resposta", customer["average_first_response_seconds"], "seconds", period=period))
                if MetricCode.TOP_TOPICS in metrics:
                    for rank, topic in enumerate(customer["top_topics"], start=1):
                        rows.append(self._metric_row("customer", scope_id, scope_label, MetricCode.TOP_TOPICS, "Assuntos principais", topic["ticket_count"], "tickets", dimension=topic["tag"], rank=rank, period=period))
            if not result["has_next"]:
                break
            page += 1
        return rows

    @staticmethod
    def _period(input_dto: MetricExportInput) -> tuple[str | None, str | None]:
        return (
            input_dto.filters.from_at.isoformat() if input_dto.filters.from_at else None,
            input_dto.filters.to_at.isoformat() if input_dto.filters.to_at else None,
        )

    @staticmethod
    def _metric_row(
        scope_type: str,
        scope_id: str,
        scope_label: str,
        metric_code: MetricCode,
        metric_label: str,
        value: Any,
        unit: str,
        *,
        numerator: Any = None,
        denominator: Any = None,
        sample_size: Any = None,
        dimension: Any = None,
        rank: Any = None,
        period: tuple[str | None, str | None],
    ) -> dict[str, Any]:
        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "scope_label": scope_label,
            "metric_code": metric_code.value,
            "metric_label": metric_label,
            "value": value,
            "unit": unit,
            "numerator": numerator,
            "denominator": denominator,
            "sample_size": sample_size,
            "dimension": dimension,
            "rank": rank,
            "period_start": period[0],
            "period_end": period[1],
        }
