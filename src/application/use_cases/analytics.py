from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.application.contracts.repositories import (
    CustomerRepository,
    TagRepository,
    TicketRepository,
)
from src.application.dtos.analytics import (
    AnalyticsFilters,
    AverageFirstResponseMetric,
    AverageRecurrenceMetric,
    BasicDistributionPoint,
    CustomerAnalyticsRow,
    CustomerBehaviorOutput,
    CustomerMetricsInput,
    CustomerMetricsItem,
    CustomerMetricsPage,
    DashboardChartsOutput,
    DashboardFilterOptionsOutput,
    DashboardInput,
    DashboardMetricsOutput,
    DashboardOperationalSnapshot,
    DashboardOutput,
    DashboardPeriodSnapshot,
    DashboardScopeOutput,
    DashboardSummaryOutput,
    DashboardTopDriver,
    DistributionPoint,
    FirstResponseDistributionPoint,
    OperationTimeseriesPoint,
    PriorityBreakdownPoint,
    ResolutionRateMetric,
    SatisfactionRateMetric,
    TicketVolumeMetric,
    TicketsOverTimePoint,
    TopCustomerOutput,
    TopicBreakdownPoint,
)


_RESPONSE_BUCKETS = (
    ("up_to_15m", "Até 15 min"),
    ("15_to_30m", "15 a 30 min"),
    ("30_to_60m", "30 a 60 min"),
    ("1_to_4h", "1 a 4 h"),
    ("over_4h", "Acima de 4 h"),
    ("unanswered", "Sem resposta válida"),
)
_CUSTOMER_METRICS_BATCH_SIZE = 100


class AnalyticsCalculator:
    @staticmethod
    def rate(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    @staticmethod
    def change_percent(
        current: float | int | None,
        previous: float | int | None,
    ) -> float | None:
        if current is None or previous in (None, 0):
            return None
        return round(
            ((float(current) - float(previous)) / abs(float(previous))) * 100,
            2,
        )

    @staticmethod
    def change_points(
        current: float | None,
        previous: float | None,
    ) -> float | None:
        if current is None or previous is None:
            return None
        return round((float(current) - float(previous)) * 100, 2)

    @classmethod
    def build_metrics(
        cls,
        current: DashboardPeriodSnapshot,
        previous: DashboardPeriodSnapshot | None,
    ) -> DashboardMetricsOutput:
        current_resolution = cls.rate(
            current.resolved_tickets,
            current.total_tickets,
        )
        previous_resolution = (
            cls.rate(previous.resolved_tickets, previous.total_tickets)
            if previous
            else None
        )
        current_rated = current.good_ratings + current.bad_ratings
        previous_rated = (
            previous.good_ratings + previous.bad_ratings if previous else 0
        )
        current_satisfaction = cls.rate(current.good_ratings, current_rated)
        previous_satisfaction = (
            cls.rate(previous.good_ratings, previous_rated) if previous else None
        )

        return DashboardMetricsOutput(
            ticket_volume=TicketVolumeMetric(
                value=current.total_tickets,
                previous_value=previous.total_tickets if previous else None,
                change_percent=cls.change_percent(
                    current.total_tickets,
                    previous.total_tickets if previous else None,
                ),
            ),
            average_recurrence=AverageRecurrenceMetric(
                average_seconds=current.average_recurrence_seconds,
                sample_intervals=current.recurrence_sample_intervals,
                customers_with_recurrence=current.customers_with_recurrence,
                previous_average_seconds=(
                    previous.average_recurrence_seconds if previous else None
                ),
                change_percent=cls.change_percent(
                    current.average_recurrence_seconds,
                    previous.average_recurrence_seconds if previous else None,
                ),
            ),
            resolution_rate=ResolutionRateMetric(
                rate=current_resolution,
                resolved=current.resolved_tickets,
                total=current.total_tickets,
                previous_rate=previous_resolution,
                change_percent=cls.change_percent(
                    current_resolution,
                    previous_resolution,
                ),
                change_points=cls.change_points(
                    current_resolution,
                    previous_resolution,
                ),
            ),
            satisfaction_rate=SatisfactionRateMetric(
                rate=current_satisfaction,
                good=current.good_ratings,
                bad=current.bad_ratings,
                rated_total=current_rated,
                previous_rate=previous_satisfaction,
                change_percent=cls.change_percent(
                    current_satisfaction,
                    previous_satisfaction,
                ),
                change_points=cls.change_points(
                    current_satisfaction,
                    previous_satisfaction,
                ),
            ),
            average_first_response=AverageFirstResponseMetric(
                average_seconds=current.average_first_response_seconds,
                responded_tickets=current.responded_tickets,
                unanswered_tickets=max(
                    current.total_tickets - current.responded_tickets,
                    0,
                ),
                previous_average_seconds=(
                    previous.average_first_response_seconds if previous else None
                ),
                change_percent=cls.change_percent(
                    current.average_first_response_seconds,
                    previous.average_first_response_seconds if previous else None,
                ),
            ),
        )

    @classmethod
    def build_customer_item(
        cls,
        row: CustomerAnalyticsRow,
    ) -> CustomerMetricsItem:
        rated_total = row.good_ratings + row.bad_ratings
        return CustomerMetricsItem(
            customer_id=row.customer_id,
            external_requester_id=row.external_requester_id,
            requester_name=row.requester_name,
            requester_email=row.requester_email,
            ticket_volume=row.ticket_volume,
            average_recurrence_seconds=row.average_recurrence_seconds,
            recurrence_sample_intervals=row.recurrence_sample_intervals,
            resolution_rate=cls.rate(
                row.resolved_tickets,
                row.ticket_volume,
            ),
            resolved_tickets=row.resolved_tickets,
            satisfaction_rate=cls.rate(
                row.good_ratings,
                rated_total,
            ),
            good_ratings=row.good_ratings,
            bad_ratings=row.bad_ratings,
            average_first_response_seconds=(
                row.average_first_response_seconds
            ),
            top_topics=row.top_topics,
        )


class GetDashboardOverview:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        customer_repository: CustomerRepository,
        tag_repository: TagRepository,
    ) -> None:
        self._tickets = ticket_repository
        self._customers = customer_repository
        self._tags = tag_repository

    async def execute(self, input_dto: DashboardInput) -> DashboardOutput:
        filters = input_dto.filters()
        previous_filters = self._previous_filters(filters)

        current = await self._tickets.get_dashboard_period_snapshot(
            filters,
            input_dto.top_topics_limit,
        )
        previous = (
            await self._tickets.get_dashboard_period_snapshot(
                previous_filters,
                input_dto.top_topics_limit,
            )
            if previous_filters is not None
            else None
        )
        operational = await self._tickets.get_dashboard_operational_snapshot(
            filters,
            input_dto.timeline_limit,
        )
        customer_options = await self._customers.list_filter_options()
        tag_options = await self._tags.list_filter_options()
        assignee_options = await self._tickets.list_assignee_options()

        metrics = AnalyticsCalculator.build_metrics(current, previous)
        charts = self._build_charts(current, previous, operational)
        summary = self._build_summary(metrics, charts.top_topics)

        return DashboardOutput(
            filters=filters.model_dump(mode="json"),
            metrics=metrics,
            charts=charts,
            customer_behavior=CustomerBehaviorOutput(
                unique_customers=operational.unique_customers,
                repeat_customers=operational.repeat_customers,
                repeat_customer_rate=AnalyticsCalculator.rate(
                    operational.repeat_customers,
                    operational.unique_customers,
                ),
                average_tickets_per_customer=(
                    round(operational.average_tickets_per_customer, 2)
                    if operational.average_tickets_per_customer is not None
                    else None
                ),
                top_customers=[
                    TopCustomerOutput(
                        customer_id=item.customer_id,
                        requester_name=item.requester_name,
                        requester_email=item.requester_email,
                        ticket_count=item.ticket_count,
                    )
                    for item in operational.top_customers
                ],
            ),
            scope=DashboardScopeOutput(
                from_at=filters.from_at,
                to_at=filters.to_at,
                previous_from_at=(
                    previous_filters.from_at if previous_filters else None
                ),
                previous_to_at=(
                    previous_filters.to_at if previous_filters else None
                ),
                is_comparable=previous_filters is not None,
            ),
            summary=summary,
            filter_options=DashboardFilterOptionsOutput(
                tags=[
                    {"id": str(option.id), "name": option.name}
                    for option in tag_options
                ],
                customers=[
                    {
                        "id": str(option.id),
                        "requester_name": option.requester_name,
                        "requester_email": option.requester_email,
                    }
                    for option in customer_options
                ],
                assignees=[
                    {
                        "external_id": option.external_id,
                        "name": option.name or f"Responsável {option.external_id}",
                    }
                    for option in assignee_options
                ],
            ),
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _previous_filters(filters: AnalyticsFilters) -> AnalyticsFilters | None:
        if filters.from_at is None or filters.to_at is None:
            return None
        duration = filters.to_at - filters.from_at
        if duration.total_seconds() <= 0:
            return None
        previous_to = filters.from_at - timedelta(microseconds=1)
        previous_from = previous_to - duration
        return filters.model_copy(
            update={"from_at": previous_from, "to_at": previous_to}
        )

    def _build_charts(
        self,
        current: DashboardPeriodSnapshot,
        previous: DashboardPeriodSnapshot | None,
        operational: DashboardOperationalSnapshot,
    ) -> DashboardChartsOutput:
        previous_statuses = (
            {item.label: item.value for item in previous.status_counts}
            if previous
            else {}
        )
        previous_priorities = (
            {
                item.priority: item.ticket_count
                for item in previous.priority_aggregates
            }
            if previous
            else {}
        )
        previous_topics = (
            {item.tag: item.ticket_count for item in previous.topic_aggregates}
            if previous
            else {}
        )
        response_counts = {
            item.bucket: item.ticket_count
            for item in operational.response_buckets
        }

        status_distribution = []
        for item in current.status_counts:
            previous_value = (
                previous_statuses.get(item.label, 0) if previous else None
            )
            status_distribution.append(
                DistributionPoint(
                    label=item.label,
                    value=item.value,
                    previous_value=previous_value,
                    change_percent=AnalyticsCalculator.change_percent(
                        item.value,
                        previous_value,
                    ),
                )
            )

        priority_breakdown = []
        for item in current.priority_aggregates:
            previous_value = (
                previous_priorities.get(item.priority, 0)
                if previous
                else None
            )
            priority_breakdown.append(
                PriorityBreakdownPoint(
                    priority=item.priority,
                    ticket_count=item.ticket_count,
                    share=AnalyticsCalculator.rate(
                        item.ticket_count,
                        current.total_tickets,
                    ),
                    resolved_tickets=item.resolved_tickets,
                    resolution_rate=AnalyticsCalculator.rate(
                        item.resolved_tickets,
                        item.ticket_count,
                    ),
                    average_first_response_seconds=(
                        round(item.average_first_response_seconds, 2)
                        if item.average_first_response_seconds is not None
                        else None
                    ),
                    previous_ticket_count=previous_value,
                    change_percent=AnalyticsCalculator.change_percent(
                        item.ticket_count,
                        previous_value,
                    ),
                )
            )

        topics = []
        for rank, item in enumerate(current.topic_aggregates, start=1):
            previous_value = (
                previous_topics.get(item.tag, 0) if previous else None
            )
            topics.append(
                TopicBreakdownPoint(
                    tag=item.tag,
                    ticket_count=item.ticket_count,
                    share=AnalyticsCalculator.rate(
                        item.ticket_count,
                        current.total_tickets,
                    ),
                    resolved_tickets=item.resolved_tickets,
                    resolution_rate=AnalyticsCalculator.rate(
                        item.resolved_tickets,
                        item.ticket_count,
                    ),
                    average_first_response_seconds=(
                        round(item.average_first_response_seconds, 2)
                        if item.average_first_response_seconds is not None
                        else None
                    ),
                    rank=rank,
                    previous_ticket_count=previous_value,
                    change_percent=AnalyticsCalculator.change_percent(
                        item.ticket_count,
                        previous_value,
                    ),
                )
            )

        return DashboardChartsOutput(
            tickets_over_time=[
                TicketsOverTimePoint(date=item.date, value=item.opened)
                for item in operational.timeline
            ],
            status_distribution=status_distribution,
            priority_distribution=[
                BasicDistributionPoint(
                    label=item.priority,
                    value=item.ticket_count,
                )
                for item in current.priority_aggregates
            ],
            operation_timeseries=[
                OperationTimeseriesPoint(
                    date=item.date,
                    opened=item.opened,
                    resolved=item.resolved,
                    resolution_rate=AnalyticsCalculator.rate(
                        item.resolved,
                        item.opened,
                    ),
                    average_first_response_seconds=(
                        round(item.average_first_response_seconds, 2)
                        if item.average_first_response_seconds is not None
                        else None
                    ),
                    satisfaction_rate=AnalyticsCalculator.rate(
                        item.good_ratings,
                        item.good_ratings + item.bad_ratings,
                    ),
                    rated_tickets=item.good_ratings + item.bad_ratings,
                )
                for item in operational.timeline
            ],
            priority_breakdown=priority_breakdown,
            first_response_distribution=[
                FirstResponseDistributionPoint(
                    bucket=bucket,
                    label=label,
                    ticket_count=response_counts.get(bucket, 0),
                    share=AnalyticsCalculator.rate(
                        response_counts.get(bucket, 0),
                        current.total_tickets,
                    ),
                )
                for bucket, label in _RESPONSE_BUCKETS
            ],
            top_topics=topics,
        )

    def _build_summary(
        self,
        metrics: DashboardMetricsOutput,
        topics: list[TopicBreakdownPoint],
    ) -> DashboardSummaryOutput:
        volume = metrics.ticket_volume
        resolution = metrics.resolution_rate
        response = metrics.average_first_response
        satisfaction = metrics.satisfaction_rate
        top_topic = topics[0] if topics else None

        fragments = [
            self._movement("O volume", volume.change_percent, neutral=True),
            self._movement_points(
                "A taxa de resolução",
                resolution.change_points,
            ),
            self._duration_movement(
                "O tempo médio até a primeira resposta",
                response.change_percent,
            ),
        ]
        headline = " ".join(
            fragment for fragment in fragments if fragment
        )

        alerts: list[tuple[float, str]] = []
        improvements: list[tuple[float, str]] = []
        if resolution.change_points is not None:
            points = float(resolution.change_points)
            target = improvements if points > 0 else alerts
            target.append(
                (
                    abs(points),
                    f"Resolução {'subiu' if points > 0 else 'caiu'} "
                    f"{abs(points):.1f} p.p.",
                )
            )
        if response.change_percent is not None:
            change = float(response.change_percent)
            target = alerts if change > 0 else improvements
            target.append(
                (
                    abs(change),
                    f"Primeira resposta ficou {abs(change):.1f}% "
                    f"{'mais lenta' if change > 0 else 'mais rápida'}.",
                )
            )
        if satisfaction.change_points is not None:
            points = float(satisfaction.change_points)
            target = improvements if points > 0 else alerts
            target.append(
                (
                    abs(points),
                    f"Satisfação {'subiu' if points > 0 else 'caiu'} "
                    f"{abs(points):.1f} p.p.",
                )
            )

        return DashboardSummaryOutput(
            headline=(
                headline
                or "O período não possui uma base anterior comparável."
            ),
            primary_alert=max(
                alerts,
                default=(
                    0,
                    "Nenhuma deterioração relevante foi detectada.",
                ),
            )[1],
            primary_improvement=max(
                improvements,
                default=(
                    0,
                    "Nenhuma melhora relevante foi detectada.",
                ),
            )[1],
            top_driver=(
                DashboardTopDriver(
                    label=top_topic.tag,
                    ticket_count=top_topic.ticket_count,
                    share=top_topic.share,
                    change_percent=top_topic.change_percent,
                )
                if top_topic
                else None
            ),
        )

    @staticmethod
    def _movement(
        label: str,
        change: float | None,
        *,
        neutral: bool = False,
    ) -> str:
        if change is None:
            return f"{label} não tem base anterior comparável."
        if abs(change) < 0.05:
            return f"{label} permaneceu estável."
        direction = "aumentou" if change > 0 else "caiu"
        suffix = "" if neutral else " no período"
        return f"{label} {direction} {abs(change):.1f}%{suffix}."

    @staticmethod
    def _movement_points(label: str, change: float | None) -> str:
        if change is None:
            return f"{label} não tem base anterior comparável."
        if abs(change) < 0.05:
            return f"{label} permaneceu estável."
        direction = "subiu" if change > 0 else "caiu"
        return f"{label} {direction} {abs(change):.1f} p.p."

    @staticmethod
    def _duration_movement(label: str, change: float | None) -> str:
        if change is None:
            return f"{label} não tem base anterior comparável."
        if abs(change) < 0.05:
            return f"{label} permaneceu estável."
        return (
            f"{label} ficou {abs(change):.1f}% "
            f"{'mais lento' if change > 0 else 'mais rápido'}."
        )


class ListCustomerMetrics:
    def __init__(self, ticket_repository: TicketRepository) -> None:
        self._tickets = ticket_repository

    async def execute(
        self,
        input_dto: CustomerMetricsInput,
    ) -> CustomerMetricsPage:
        if not self._has_metric_filters(input_dto):
            result = await self._tickets.page_customer_analytics(input_dto)
            return CustomerMetricsPage(
                items=[
                    AnalyticsCalculator.build_customer_item(item)
                    for item in result.items
                ],
                page=result.page,
                page_size=result.page_size,
                total=result.total,
                has_next=result.has_next,
                has_previous=result.has_previous,
            )

        rows: list[CustomerAnalyticsRow] = []
        repository_page = 1
        while True:
            repository_input = input_dto.model_copy(
                update={
                    "page": repository_page,
                    "page_size": _CUSTOMER_METRICS_BATCH_SIZE,
                }
            )
            result = await self._tickets.page_customer_analytics(repository_input)
            rows.extend(result.items)
            if not result.has_next:
                break
            repository_page += 1

        filtered_items = [
            item
            for item in (
                AnalyticsCalculator.build_customer_item(row) for row in rows
            )
            if self._matches_metric_filters(item, input_dto)
        ]
        offset = (input_dto.page - 1) * input_dto.page_size
        page_items = filtered_items[offset : offset + input_dto.page_size]
        total = len(filtered_items)
        return CustomerMetricsPage(
            items=page_items,
            page=input_dto.page,
            page_size=input_dto.page_size,
            total=total,
            has_next=offset + len(page_items) < total,
            has_previous=input_dto.page > 1,
        )

    @staticmethod
    def _has_metric_filters(input_dto: CustomerMetricsInput) -> bool:
        return any(
            value is not None
            for value in (
                input_dto.ticket_volume_min,
                input_dto.ticket_volume_max,
                input_dto.satisfaction_rate_min,
                input_dto.satisfaction_rate_max,
            )
        )

    @staticmethod
    def _matches_metric_filters(
        item: CustomerMetricsItem,
        filters: CustomerMetricsInput,
    ) -> bool:
        if (
            filters.ticket_volume_min is not None
            and item.ticket_volume < filters.ticket_volume_min
        ):
            return False
        if (
            filters.ticket_volume_max is not None
            and item.ticket_volume > filters.ticket_volume_max
        ):
            return False
        if filters.satisfaction_rate_min is not None:
            if (
                item.satisfaction_rate is None
                or item.satisfaction_rate < filters.satisfaction_rate_min
            ):
                return False
        if filters.satisfaction_rate_max is not None:
            if (
                item.satisfaction_rate is None
                or item.satisfaction_rate > filters.satisfaction_rate_max
            ):
                return False
        return True
