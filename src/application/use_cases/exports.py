from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from src.application.contracts.reports import ReportWriterFactory
from src.application.contracts.repositories import (
    CustomerRepository,
    TagRepository,
    TicketRepository,
)
from src.application.dtos.analytics import CustomerMetricsInput, ExportTicketRecord
from src.application.dtos.exports import (
    DataExportInput,
    DataExportPreviewInput,
    DataExportPreviewOutput,
    ExportedFile,
    MetricsExportInput,
)
from src.application.use_cases.analytics import AnalyticsCalculator
from src.domain.analytics import (
    DEFAULT_DATA_EXPORT_FIELDS,
    DEFAULT_METRICS,
    ESSENTIAL_DATA_EXPORT_FIELDS,
    SERVICE_DATA_EXPORT_FIELDS,
    DataExportField,
    MetricCode,
    ReportFormat,
    ReportScope,
)
from src.domain.entities import SatisfactionScore, TicketPriority, TicketStatus


_MEDIA_TYPES = {
    ReportFormat.CSV: "text/csv; charset=utf-8",
    ReportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_FIELD_LABELS = {
    "ticket_id": "ID do ticket",
    "subject": "Assunto",
    "description": "Descrição",
    "status": "Status",
    "priority": "Prioridade",
    "requester_id": "ID do cliente",
    "requester_name": "Cliente",
    "requester_email": "E-mail do cliente",
    "assignee_id": "ID do responsável",
    "assignee_name": "Responsável",
    "created_at": "Criado em",
    "updated_at": "Atualizado em",
    "first_response_at": "Primeira resposta em",
    "tags": "Tags",
    "satisfaction_rating": "Avaliação de satisfação",
}

_METRIC_CATALOG = (
    (MetricCode.TICKET_VOLUME, "Volume de tickets", "tickets"),
    (MetricCode.AVERAGE_RECURRENCE_SECONDS, "Frequência média", "seconds"),
    (MetricCode.TOP_TOPICS, "Assuntos principais", "tickets"),
    (MetricCode.RESOLUTION_RATE, "Taxa de resolução", "ratio"),
    (MetricCode.SATISFACTION_RATE, "Índice de satisfação", "ratio"),
    (
        MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS,
        "Tempo médio até a primeira resposta",
        "seconds",
    ),
)

_FIELD_PRESETS = (
    (
        "essential",
        "Essencial",
        "Colunas principais para análise rápida de tickets.",
        ESSENTIAL_DATA_EXPORT_FIELDS,
    ),
    (
        "service",
        "Atendimento",
        "Inclui descrição, contato, datas e dados do atendimento.",
        SERVICE_DATA_EXPORT_FIELDS,
    ),
    (
        "complete",
        "Completo",
        "Inclui todos os campos disponíveis no sistema.",
        DEFAULT_DATA_EXPORT_FIELDS,
    ),
)


class GetExportCatalog:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        customer_repository: CustomerRepository,
        tag_repository: TagRepository,
    ) -> None:
        self._tickets = ticket_repository
        self._customers = customer_repository
        self._tags = tag_repository

    async def execute(self) -> dict[str, Any]:
        tags = await self._tags.list_filter_options()
        customers = await self._customers.list_filter_options()
        assignees = await self._tickets.list_assignee_options()
        return {
            "formats": [
                {
                    "code": report_format.value,
                    "label": (
                        "CSV"
                        if report_format == ReportFormat.CSV
                        else "Excel (.xlsx)"
                    ),
                    "media_type": _MEDIA_TYPES[report_format],
                }
                for report_format in ReportFormat
            ],
            "fields": [
                {"code": field.value, "label": _FIELD_LABELS[field.value]}
                for field in DEFAULT_DATA_EXPORT_FIELDS
            ],
            "field_presets": [
                {
                    "code": code,
                    "label": label,
                    "description": description,
                    "fields": [field.value for field in fields],
                }
                for code, label, description, fields in _FIELD_PRESETS
            ],
            "metrics": [
                {"code": code.value, "label": label, "unit": unit}
                for code, label, unit in _METRIC_CATALOG
            ],
            "scopes": [
                {"code": ReportScope.OVERALL.value, "label": "Visão geral"},
                {"code": ReportScope.CUSTOMER.value, "label": "Por cliente"},
            ],
            "statuses": [
                {
                    "code": item.value,
                    "label": item.value.replace("_", " ").title(),
                }
                for item in TicketStatus
            ],
            "priorities": [
                {
                    "code": item.value,
                    "label": item.value.replace("_", " ").title(),
                }
                for item in TicketPriority
            ],
            "satisfaction_scores": [
                {
                    "code": item.value,
                    "label": item.value.replace("_", " ").title(),
                }
                for item in SatisfactionScore
            ],
            "defaults": {
                "data_format": ReportFormat.CSV.value,
                "metrics_format": ReportFormat.XLSX.value,
                "period_days": 30,
                "field_preset": "essential",
                "scope": ReportScope.OVERALL.value,
                "metrics": [metric.value for metric in DEFAULT_METRICS],
            },
            "filter_options": {
                "tags": [
                    {"id": str(option.id), "name": option.name}
                    for option in tags
                ],
                "customers": [
                    {
                        "id": str(option.id),
                        "requester_name": option.requester_name,
                        "requester_email": option.requester_email,
                    }
                    for option in customers
                ],
                "assignees": [
                    {
                        "external_id": option.external_id,
                        "name": option.name
                        or f"Responsável {option.external_id}",
                    }
                    for option in assignees
                ],
            },
        }


class PreviewDataExport:
    def __init__(self, ticket_repository: TicketRepository) -> None:
        self._tickets = ticket_repository

    async def execute(
        self,
        input_dto: DataExportPreviewInput,
    ) -> DataExportPreviewOutput:
        total = await self._tickets.count_export_rows(input_dto.filters)
        records = await self._tickets.fetch_export_records(
            input_dto.filters,
            input_dto.limit,
            0,
        )
        rows = [
            _serialize_export_record(record, input_dto.fields)
            for record in records
        ]
        return DataExportPreviewOutput(
            total_matching=total,
            preview_count=len(rows),
            fields=[field.value for field in input_dto.fields],
            items=rows,
        )


class ExportData:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        writer_factory: ReportWriterFactory,
        batch_size: int = 1000,
    ) -> None:
        self._tickets = ticket_repository
        self._writer_factory = writer_factory
        self._batch_size = batch_size

    async def execute(self, input_dto: DataExportInput) -> ExportedFile:
        columns = [field.value for field in input_dto.fields]
        writer = self._writer_factory.create_streaming(input_dto.format)
        stream = await writer.write(
            self._row_batches(input_dto),
            columns,
            "Tickets",
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return ExportedFile(
            filename=(
                f"tickets-detalhados-{timestamp}.{input_dto.format.value}"
            ),
            media_type=_MEDIA_TYPES[input_dto.format],
            stream=stream,
        )

    async def _row_batches(
        self,
        input_dto: DataExportInput,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        async for records in self._tickets.iterate_export_records(
            input_dto.filters,
            self._batch_size,
        ):
            yield [
                _serialize_export_record(record, input_dto.fields)
                for record in records
            ]


class ExportMetrics:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        writer_factory: ReportWriterFactory,
        batch_size: int = 100,
    ) -> None:
        self._tickets = ticket_repository
        self._writer_factory = writer_factory
        self._batch_size = batch_size

    async def execute(self, input_dto: MetricsExportInput) -> ExportedFile:
        metrics = input_dto.metrics or list(DEFAULT_METRICS)
        row_batches = (
            self._overall_batches(input_dto, metrics)
            if input_dto.scope == ReportScope.OVERALL
            else self._customer_batches(input_dto, metrics)
        )
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
        writer = self._writer_factory.create_streaming(input_dto.format)
        stream = await writer.write(row_batches, columns, "Metricas")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        scope_label = (
            "visao-geral"
            if input_dto.scope == ReportScope.OVERALL
            else "por-cliente"
        )
        return ExportedFile(
            filename=(
                f"metricas-{scope_label}-{timestamp}.{input_dto.format.value}"
            ),
            media_type=_MEDIA_TYPES[input_dto.format],
            stream=stream,
        )

    async def _overall_batches(
        self,
        input_dto: MetricsExportInput,
        metrics: list[MetricCode],
    ) -> AsyncIterator[list[dict[str, Any]]]:
        yield await self._overall_rows(input_dto, metrics)

    async def _customer_batches(
        self,
        input_dto: MetricsExportInput,
        metrics: list[MetricCode],
    ) -> AsyncIterator[list[dict[str, Any]]]:
        page = 1
        period = self._period(input_dto)
        while True:
            page_input = CustomerMetricsInput(
                **input_dto.filters.model_dump(),
                page=page,
                page_size=self._batch_size,
                top_topics_limit=input_dto.top_topics_limit,
            )
            result = await self._tickets.page_customer_analytics(page_input)
            rows: list[dict[str, Any]] = []
            for raw_customer in result.items:
                customer = AnalyticsCalculator.build_customer_item(raw_customer)
                rows.extend(
                    self._customer_metric_rows(
                        customer,
                        metrics,
                        period,
                    )
                )
            if rows:
                yield rows
            if not result.has_next:
                return
            page += 1

    async def _overall_rows(
        self,
        input_dto: MetricsExportInput,
        metrics: list[MetricCode],
    ) -> list[dict[str, Any]]:
        snapshot = await self._tickets.get_dashboard_period_snapshot(
            input_dto.filters,
            input_dto.top_topics_limit,
        )
        period = self._period(input_dto)
        rows: list[dict[str, Any]] = []
        if MetricCode.TICKET_VOLUME in metrics:
            rows.append(
                self._metric_row(
                    "overall",
                    "all",
                    "Visão geral",
                    MetricCode.TICKET_VOLUME,
                    "Volume de tickets",
                    snapshot.total_tickets,
                    "tickets",
                    period=period,
                )
            )
        if MetricCode.AVERAGE_RECURRENCE_SECONDS in metrics:
            rows.append(
                self._metric_row(
                    "overall",
                    "all",
                    "Visão geral",
                    MetricCode.AVERAGE_RECURRENCE_SECONDS,
                    "Frequência média",
                    snapshot.average_recurrence_seconds,
                    "seconds",
                    sample_size=snapshot.recurrence_sample_intervals,
                    period=period,
                )
            )
        if MetricCode.RESOLUTION_RATE in metrics:
            rows.append(
                self._metric_row(
                    "overall",
                    "all",
                    "Visão geral",
                    MetricCode.RESOLUTION_RATE,
                    "Taxa de resolução",
                    AnalyticsCalculator.rate(
                        snapshot.resolved_tickets,
                        snapshot.total_tickets,
                    ),
                    "ratio",
                    numerator=snapshot.resolved_tickets,
                    denominator=snapshot.total_tickets,
                    period=period,
                )
            )
        if MetricCode.SATISFACTION_RATE in metrics:
            rated_total = snapshot.good_ratings + snapshot.bad_ratings
            rows.append(
                self._metric_row(
                    "overall",
                    "all",
                    "Visão geral",
                    MetricCode.SATISFACTION_RATE,
                    "Índice de satisfação",
                    AnalyticsCalculator.rate(snapshot.good_ratings, rated_total),
                    "ratio",
                    numerator=snapshot.good_ratings,
                    denominator=rated_total,
                    sample_size=rated_total,
                    period=period,
                )
            )
        if MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS in metrics:
            rows.append(
                self._metric_row(
                    "overall",
                    "all",
                    "Visão geral",
                    MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS,
                    "Tempo médio até a primeira resposta",
                    snapshot.average_first_response_seconds,
                    "seconds",
                    sample_size=snapshot.responded_tickets,
                    period=period,
                )
            )
        if MetricCode.TOP_TOPICS in metrics:
            for rank, topic in enumerate(snapshot.topic_aggregates, start=1):
                rows.append(
                    self._metric_row(
                        "overall",
                        "all",
                        "Visão geral",
                        MetricCode.TOP_TOPICS,
                        "Assuntos principais",
                        topic.ticket_count,
                        "tickets",
                        dimension=topic.tag,
                        rank=rank,
                        period=period,
                    )
                )
        return rows

    def _customer_metric_rows(
        self,
        customer,
        metrics: list[MetricCode],
        period: tuple[str | None, str | None],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        scope_id = str(customer.customer_id)
        scope_label = (
            f"{customer.requester_name} <{customer.requester_email}>"
        )
        if MetricCode.TICKET_VOLUME in metrics:
            rows.append(
                self._metric_row(
                    "customer",
                    scope_id,
                    scope_label,
                    MetricCode.TICKET_VOLUME,
                    "Volume de tickets",
                    customer.ticket_volume,
                    "tickets",
                    period=period,
                )
            )
        if MetricCode.AVERAGE_RECURRENCE_SECONDS in metrics:
            rows.append(
                self._metric_row(
                    "customer",
                    scope_id,
                    scope_label,
                    MetricCode.AVERAGE_RECURRENCE_SECONDS,
                    "Frequência média",
                    customer.average_recurrence_seconds,
                    "seconds",
                    sample_size=customer.recurrence_sample_intervals,
                    period=period,
                )
            )
        if MetricCode.RESOLUTION_RATE in metrics:
            rows.append(
                self._metric_row(
                    "customer",
                    scope_id,
                    scope_label,
                    MetricCode.RESOLUTION_RATE,
                    "Taxa de resolução",
                    customer.resolution_rate,
                    "ratio",
                    numerator=customer.resolved_tickets,
                    denominator=customer.ticket_volume,
                    period=period,
                )
            )
        if MetricCode.SATISFACTION_RATE in metrics:
            rated_total = customer.good_ratings + customer.bad_ratings
            rows.append(
                self._metric_row(
                    "customer",
                    scope_id,
                    scope_label,
                    MetricCode.SATISFACTION_RATE,
                    "Índice de satisfação",
                    customer.satisfaction_rate,
                    "ratio",
                    numerator=customer.good_ratings,
                    denominator=rated_total,
                    sample_size=rated_total,
                    period=period,
                )
            )
        if MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS in metrics:
            rows.append(
                self._metric_row(
                    "customer",
                    scope_id,
                    scope_label,
                    MetricCode.AVERAGE_FIRST_RESPONSE_SECONDS,
                    "Tempo médio até a primeira resposta",
                    customer.average_first_response_seconds,
                    "seconds",
                    period=period,
                )
            )
        if MetricCode.TOP_TOPICS in metrics:
            for rank, topic in enumerate(customer.top_topics, start=1):
                rows.append(
                    self._metric_row(
                        "customer",
                        scope_id,
                        scope_label,
                        MetricCode.TOP_TOPICS,
                        "Assuntos principais",
                        topic.ticket_count,
                        "tickets",
                        dimension=topic.tag,
                        rank=rank,
                        period=period,
                    )
                )
        return rows

    @staticmethod
    def _period(
        input_dto: MetricsExportInput,
    ) -> tuple[str | None, str | None]:
        return (
            input_dto.filters.from_at.isoformat()
            if input_dto.filters.from_at
            else None,
            input_dto.filters.to_at.isoformat()
            if input_dto.filters.to_at
            else None,
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


def _serialize_export_record(
    record: ExportTicketRecord,
    fields: list[DataExportField],
) -> dict[str, Any]:
    rating = None
    if record.satisfaction_rating is not None:
        rating = {
            "score": record.satisfaction_rating.score.lower(),
            "offered_at": _iso(record.satisfaction_rating.offered_at),
            "rated_at": _iso(record.satisfaction_rating.rated_at),
            "comment": record.satisfaction_rating.comment,
        }
    complete = {
        "ticket_id": record.ticket_id,
        "subject": record.subject,
        "description": record.description,
        "status": record.status.lower(),
        "priority": record.priority.lower(),
        "requester_id": record.requester_id,
        "requester_name": record.requester_name,
        "requester_email": record.requester_email,
        "assignee_id": record.assignee_id,
        "assignee_name": record.assignee_name,
        "created_at": _iso(record.created_at),
        "updated_at": _iso(record.updated_at),
        "first_response_at": _iso(record.first_response_at),
        "tags": record.tags,
        "satisfaction_rating": rating,
    }
    return {field.value: complete[field.value] for field in fields}


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
