from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select

from src.application.dtos.analytics import AnalyticsFilters
from src.domain.analytics import RATED_SATISFACTION_SCORES, RESOLVED_STATUSES
from src.infra.database.analytics import SqlAlchemyAnalyticsQueryRepository
from src.infra.database.models import Customer, SatisfactionRating, Tag, Ticket, TicketTag


_RESPONSE_BUCKETS = (
    ("up_to_15m", "Até 15 min"),
    ("15_to_30m", "15 a 30 min"),
    ("30_to_60m", "30 a 60 min"),
    ("1_to_4h", "1 a 4 h"),
    ("over_4h", "Acima de 4 h"),
    ("unanswered", "Sem resposta válida"),
)


class DashboardAnalyticsQueryRepository(SqlAlchemyAnalyticsQueryRepository):
    """Read model especializado para o dashboard sem alterar os repositórios CRUD."""

    async def get_dashboard(
        self,
        filters: AnalyticsFilters,
        top_topics_limit: int,
        timeline_limit: int,
    ) -> dict[str, Any]:
        current = await super().get_dashboard(filters, top_topics_limit, timeline_limit)
        previous_filters = self._previous_filters(filters)
        previous = (
            await super().get_dashboard(previous_filters, top_topics_limit, timeline_limit)
            if previous_filters is not None
            else None
        )

        details = await self._get_operational_details(
            filters,
            top_topics_limit=top_topics_limit,
            timeline_limit=timeline_limit,
        )
        current["charts"].update(details["charts"])
        current["customer_behavior"] = details["customer_behavior"]
        current["scope"] = self._scope(filters, previous_filters)
        self._attach_comparison(current, previous)
        current["summary"] = self._build_summary(current)
        return current

    @staticmethod
    def _previous_filters(filters: AnalyticsFilters) -> AnalyticsFilters | None:
        if filters.from_at is None or filters.to_at is None:
            return None
        duration = filters.to_at - filters.from_at
        if duration.total_seconds() <= 0:
            return None
        previous_to = filters.from_at - timedelta(microseconds=1)
        previous_from = previous_to - duration
        return filters.model_copy(update={"from_at": previous_from, "to_at": previous_to})

    @staticmethod
    def _scope(
        filters: AnalyticsFilters,
        previous_filters: AnalyticsFilters | None,
    ) -> dict[str, Any]:
        return {
            "from_at": filters.from_at.isoformat() if filters.from_at else None,
            "to_at": filters.to_at.isoformat() if filters.to_at else None,
            "previous_from_at": previous_filters.from_at.isoformat()
            if previous_filters and previous_filters.from_at
            else None,
            "previous_to_at": previous_filters.to_at.isoformat()
            if previous_filters and previous_filters.to_at
            else None,
            "is_comparable": previous_filters is not None,
            "timezone": "UTC",
        }

    async def _get_operational_details(
        self,
        filters: AnalyticsFilters,
        *,
        top_topics_limit: int,
        timeline_limit: int,
    ) -> dict[str, Any]:
        predicates = self._ticket_predicates(filters)
        valid_response_seconds = case(
            (
                Ticket.first_response_at.is_not(None)
                & (Ticket.first_response_at >= Ticket.source_created_at),
                self._seconds_between(Ticket.first_response_at, Ticket.source_created_at),
            ),
            else_=None,
        )

        timeline_rows = list(
            reversed(
                (
                    await self._session.execute(
                        select(
                            func.date(Ticket.source_created_at).label("date"),
                            func.count(Ticket.id).label("opened"),
                            func.sum(case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)).label("resolved"),
                            func.avg(valid_response_seconds).label("average_first_response_seconds"),
                            func.sum(case((SatisfactionRating.score == "GOOD", 1), else_=0)).label("good"),
                            func.sum(case((SatisfactionRating.score == "BAD", 1), else_=0)).label("bad"),
                        )
                        .select_from(Ticket)
                        .outerjoin(SatisfactionRating, SatisfactionRating.ticket_id == Ticket.id)
                        .where(*predicates)
                        .group_by(func.date(Ticket.source_created_at))
                        .order_by(func.date(Ticket.source_created_at).desc())
                        .limit(timeline_limit)
                    )
                ).mappings().all()
            )
        )

        priority_rows = (
            await self._session.execute(
                select(
                    Ticket.priority.label("priority"),
                    func.count(Ticket.id).label("ticket_count"),
                    func.sum(case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)).label("resolved"),
                    func.avg(valid_response_seconds).label("average_first_response_seconds"),
                )
                .where(*predicates)
                .group_by(Ticket.priority)
                .order_by(func.count(Ticket.id).desc())
            )
        ).mappings().all()

        topic_rows = (
            await self._session.execute(
                select(
                    Tag.name.label("tag"),
                    func.count(func.distinct(Ticket.id)).label("ticket_count"),
                    func.sum(case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)).label("resolved"),
                    func.avg(valid_response_seconds).label("average_first_response_seconds"),
                )
                .select_from(Ticket)
                .join(TicketTag, TicketTag.ticket_id == Ticket.id)
                .join(Tag, Tag.id == TicketTag.tag_id)
                .where(*predicates)
                .group_by(Tag.id, Tag.name)
                .order_by(func.count(func.distinct(Ticket.id)).desc(), Tag.name.asc())
                .limit(top_topics_limit)
            )
        ).mappings().all()

        response_seconds = self._seconds_between(
            Ticket.first_response_at,
            Ticket.source_created_at,
        )
        response_bucket = case(
            (
                Ticket.first_response_at.is_(None)
                | (Ticket.first_response_at < Ticket.source_created_at),
                "unanswered",
            ),
            (response_seconds <= 15 * 60, "up_to_15m"),
            (response_seconds <= 30 * 60, "15_to_30m"),
            (response_seconds <= 60 * 60, "30_to_60m"),
            (response_seconds <= 4 * 60 * 60, "1_to_4h"),
            else_="over_4h",
        ).label("bucket")
        response_rows = (
            await self._session.execute(
                select(response_bucket, func.count(Ticket.id).label("ticket_count"))
                .where(*predicates)
                .group_by(response_bucket)
            )
        ).mappings().all()
        response_counts = {row["bucket"]: int(row["ticket_count"] or 0) for row in response_rows}

        per_customer = (
            select(
                Ticket.customer_id.label("customer_id"),
                func.count(Ticket.id).label("ticket_count"),
            )
            .where(*predicates)
            .group_by(Ticket.customer_id)
            .subquery()
        )
        behavior_row = (
            await self._session.execute(
                select(
                    func.count(per_customer.c.customer_id).label("unique_customers"),
                    func.sum(case((per_customer.c.ticket_count > 1, 1), else_=0)).label("repeat_customers"),
                    func.avg(per_customer.c.ticket_count).label("average_tickets_per_customer"),
                )
            )
        ).mappings().one()
        top_customer_rows = (
            await self._session.execute(
                select(
                    Customer.id.label("customer_id"),
                    Customer.requester_name,
                    Customer.requester_email,
                    func.count(Ticket.id).label("ticket_count"),
                )
                .select_from(Ticket)
                .join(Customer, Customer.id == Ticket.customer_id)
                .where(*predicates)
                .group_by(Customer.id, Customer.requester_name, Customer.requester_email)
                .order_by(func.count(Ticket.id).desc(), Customer.requester_name.asc())
                .limit(5)
            )
        ).mappings().all()

        total = sum(int(row["opened"] or 0) for row in timeline_rows)
        unique_customers = int(behavior_row["unique_customers"] or 0)
        repeat_customers = int(behavior_row["repeat_customers"] or 0)

        timeline = []
        for row in timeline_rows:
            opened = int(row["opened"] or 0)
            resolved = int(row["resolved"] or 0)
            good = int(row["good"] or 0)
            bad = int(row["bad"] or 0)
            average_response = row["average_first_response_seconds"]
            timeline.append(
                {
                    "date": str(row["date"]),
                    "opened": opened,
                    "resolved": resolved,
                    "resolution_rate": self._rate(resolved, opened),
                    "average_first_response_seconds": round(float(average_response), 2)
                    if average_response is not None
                    else None,
                    "satisfaction_rate": self._rate(good, good + bad),
                    "rated_tickets": good + bad,
                }
            )

        priorities = []
        for row in priority_rows:
            ticket_count = int(row["ticket_count"] or 0)
            resolved = int(row["resolved"] or 0)
            average_response = row["average_first_response_seconds"]
            priorities.append(
                {
                    "priority": self._enum_value(row["priority"]),
                    "ticket_count": ticket_count,
                    "share": self._rate(ticket_count, total),
                    "resolved_tickets": resolved,
                    "resolution_rate": self._rate(resolved, ticket_count),
                    "average_first_response_seconds": round(float(average_response), 2)
                    if average_response is not None
                    else None,
                }
            )

        topics = []
        for rank, row in enumerate(topic_rows, start=1):
            ticket_count = int(row["ticket_count"] or 0)
            resolved = int(row["resolved"] or 0)
            average_response = row["average_first_response_seconds"]
            topics.append(
                {
                    "tag": row["tag"],
                    "ticket_count": ticket_count,
                    "share": self._rate(ticket_count, total),
                    "resolved_tickets": resolved,
                    "resolution_rate": self._rate(resolved, ticket_count),
                    "average_first_response_seconds": round(float(average_response), 2)
                    if average_response is not None
                    else None,
                    "rank": rank,
                }
            )

        return {
            "charts": {
                "operation_timeseries": timeline,
                "priority_breakdown": priorities,
                "first_response_distribution": [
                    {
                        "bucket": bucket,
                        "label": label,
                        "ticket_count": response_counts.get(bucket, 0),
                        "share": self._rate(response_counts.get(bucket, 0), total),
                    }
                    for bucket, label in _RESPONSE_BUCKETS
                ],
                "top_topics": topics,
            },
            "customer_behavior": {
                "unique_customers": unique_customers,
                "repeat_customers": repeat_customers,
                "repeat_customer_rate": self._rate(repeat_customers, unique_customers),
                "average_tickets_per_customer": round(
                    float(behavior_row["average_tickets_per_customer"]), 2
                )
                if behavior_row["average_tickets_per_customer"] is not None
                else None,
                "top_customers": [
                    {
                        "customer_id": str(row["customer_id"]),
                        "requester_name": row["requester_name"],
                        "requester_email": row["requester_email"],
                        "ticket_count": int(row["ticket_count"] or 0),
                    }
                    for row in top_customer_rows
                ],
            },
        }

    def _attach_comparison(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
    ) -> None:
        current_metrics = current["metrics"]
        previous_metrics = previous["metrics"] if previous else None

        self._compare_value(
            current_metrics["ticket_volume"],
            previous_metrics["ticket_volume"] if previous_metrics else None,
            "value",
        )
        self._compare_value(
            current_metrics["average_recurrence"],
            previous_metrics["average_recurrence"] if previous_metrics else None,
            "average_seconds",
        )
        self._compare_value(
            current_metrics["resolution_rate"],
            previous_metrics["resolution_rate"] if previous_metrics else None,
            "rate",
            points=True,
        )
        self._compare_value(
            current_metrics["satisfaction_rate"],
            previous_metrics["satisfaction_rate"] if previous_metrics else None,
            "rate",
            points=True,
        )
        self._compare_value(
            current_metrics["average_first_response"],
            previous_metrics["average_first_response"] if previous_metrics else None,
            "average_seconds",
        )

        previous_status = {
            item["label"]: item["value"]
            for item in (previous or {}).get("charts", {}).get("status_distribution", [])
        }
        for item in current["charts"].get("status_distribution", []):
            previous_value = previous_status.get(item["label"], 0) if previous else None
            item["previous_value"] = previous_value
            item["change_percent"] = self._change_percent(item["value"], previous_value)

        previous_priorities = {
            item["label"]: item["value"]
            for item in (previous or {}).get("charts", {}).get("priority_distribution", [])
        }
        for item in current["charts"].get("priority_breakdown", []):
            previous_value = previous_priorities.get(item["priority"], 0) if previous else None
            item["previous_ticket_count"] = previous_value
            item["change_percent"] = self._change_percent(item["ticket_count"], previous_value)

        previous_topics = {
            item["tag"]: item["ticket_count"]
            for item in (previous or {}).get("charts", {}).get("top_topics", [])
        }
        for item in current["charts"].get("top_topics", []):
            previous_value = previous_topics.get(item["tag"], 0) if previous else None
            item["previous_ticket_count"] = previous_value
            item["change_percent"] = self._change_percent(item["ticket_count"], previous_value)

    def _compare_value(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
        key: str,
        *,
        points: bool = False,
    ) -> None:
        previous_value = previous.get(key) if previous else None
        current_value = current.get(key)
        current[f"previous_{key}"] = previous_value
        current["change_percent"] = self._change_percent(current_value, previous_value)
        current["change_points"] = (
            round((float(current_value) - float(previous_value)) * 100, 2)
            if points and current_value is not None and previous_value is not None
            else None
        )

    @staticmethod
    def _change_percent(current: Any, previous: Any) -> float | None:
        if current is None or previous in (None, 0):
            return None
        return round(((float(current) - float(previous)) / abs(float(previous))) * 100, 2)

    def _build_summary(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        metrics = dashboard["metrics"]
        volume = metrics["ticket_volume"]
        resolution = metrics["resolution_rate"]
        response = metrics["average_first_response"]
        satisfaction = metrics["satisfaction_rate"]
        top_topic = (dashboard["charts"].get("top_topics") or [None])[0]

        fragments = [self._movement("O volume", volume.get("change_percent"), neutral=True)]
        fragments.append(
            self._movement_points("A taxa de resolução", resolution.get("change_points"))
        )
        fragments.append(
            self._duration_movement(
                "O tempo médio até a primeira resposta",
                response.get("change_percent"),
            )
        )
        headline = " ".join(fragment for fragment in fragments if fragment)

        alerts: list[tuple[float, str]] = []
        improvements: list[tuple[float, str]] = []
        if resolution.get("change_points") is not None:
            points = float(resolution["change_points"])
            target = improvements if points > 0 else alerts
            target.append((abs(points), f"Resolução {'subiu' if points > 0 else 'caiu'} {abs(points):.1f} p.p."))
        if response.get("change_percent") is not None:
            change = float(response["change_percent"])
            target = alerts if change > 0 else improvements
            target.append((abs(change), f"Primeira resposta ficou {abs(change):.1f}% {'mais lenta' if change > 0 else 'mais rápida'}."))
        if satisfaction.get("change_points") is not None:
            points = float(satisfaction["change_points"])
            target = improvements if points > 0 else alerts
            target.append((abs(points), f"Satisfação {'subiu' if points > 0 else 'caiu'} {abs(points):.1f} p.p."))

        return {
            "headline": headline or "O período não possui uma base anterior comparável.",
            "primary_alert": max(alerts, default=(0, "Nenhuma deterioração relevante foi detectada."))[1],
            "primary_improvement": max(improvements, default=(0, "Nenhuma melhora relevante foi detectada."))[1],
            "top_driver": {
                "label": top_topic["tag"],
                "ticket_count": top_topic["ticket_count"],
                "share": top_topic["share"],
                "change_percent": top_topic.get("change_percent"),
            }
            if top_topic
            else None,
        }

    @staticmethod
    def _movement(label: str, change: float | None, *, neutral: bool = False) -> str:
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
        return f"{label} {'subiu' if change > 0 else 'caiu'} {abs(change):.1f} p.p."

    @staticmethod
    def _duration_movement(label: str, change: float | None) -> str:
        if change is None:
            return f"{label} não tem base anterior comparável."
        if abs(change) < 0.05:
            return f"{label} permaneceu estável."
        return f"{label} ficou {abs(change):.1f}% {'mais lento' if change > 0 else 'mais rápido'}."
