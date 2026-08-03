from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if new in content:
        return
    if old not in content:
        raise RuntimeError(f"Expected block not found in {path}: {old[:80]!r}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


def patch_repositories() -> None:
    path = ROOT / "src/infra/database/repositories.py"

    replace_once(
        path,
        "from typing import Any\n",
        "from typing import Any, overload\n",
    )

    replace_once(
        path,
        """def _naive_utc(value: datetime | None) -> datetime | None:\n    if value is None:\n        return None\n    if value.tzinfo is None:\n        return value\n    return value.astimezone(timezone.utc).replace(tzinfo=None)\n""",
        """@overload\ndef _naive_utc(value: datetime) -> datetime: ...\n\n\n@overload\ndef _naive_utc(value: None) -> None: ...\n\n\ndef _naive_utc(value: datetime | None) -> datetime | None:\n    if value is None:\n        return None\n    if value.tzinfo is None:\n        return value\n    return value.astimezone(timezone.utc).replace(tzinfo=None)\n""",
    )

    replace_once(
        path,
        """        return [\n            AssigneeFilterOption(external_id=external_id, name=name)\n            for external_id, name in rows\n        ]\n""",
        """        options: list[AssigneeFilterOption] = []\n        for external_id, name in rows:\n            if external_id is None:\n                continue\n            options.append(\n                AssigneeFilterOption(external_id=external_id, name=name)\n            )\n        return options\n""",
    )

    replace_once(
        path,
        """        if filters.from_at:\n            predicates.append(Ticket.source_created_at >= _naive_utc(filters.from_at))\n        if filters.to_at:\n            predicates.append(Ticket.source_created_at <= _naive_utc(filters.to_at))\n""",
        """        if filters.from_at is not None:\n            predicates.append(\n                Ticket.source_created_at >= _naive_utc(filters.from_at)\n            )\n        if filters.to_at is not None:\n            predicates.append(\n                Ticket.source_created_at <= _naive_utc(filters.to_at)\n            )\n""",
    )


def patch_tests() -> None:
    path = ROOT / "tests/application/use_cases/test_analytics_use_cases.py"

    replace_once(
        path,
        "from types import SimpleNamespace\n",
        "from types import SimpleNamespace\nfrom typing import cast\n",
    )

    replace_once(
        path,
        "import pytest\n\nfrom src.application.dtos.analytics import (\n",
        """import pytest\n\nfrom src.application.contracts.repositories import (\n    CustomerRepository,\n    TagRepository,\n    TicketRepository,\n)\nfrom src.application.dtos.analytics import (\n    AnalyticsFilters,\n""",
    )

    replace_once(
        path,
        """    ticket_repository = SimpleNamespace(\n        get_dashboard_period_snapshot=AsyncMock(side_effect=[current, previous]),\n        get_dashboard_operational_snapshot=AsyncMock(return_value=operational),\n        list_assignee_options=AsyncMock(\n            return_value=[AssigneeFilterOption(external_id=91, name=None)]\n        ),\n    )\n    customer_repository = SimpleNamespace(\n        list_filter_options=AsyncMock(\n            return_value=[\n                CustomerFilterOption(\n                    id=CUSTOMER_ID,\n                    requester_name=\"Cliente\",\n                    requester_email=\"cliente@example.com\",\n                )\n            ]\n        )\n    )\n    tag_repository = SimpleNamespace(\n        list_filter_options=AsyncMock(\n            return_value=[TagFilterOption(id=TAG_ID, name=\"dns\")]\n        )\n    )\n""",
        """    get_dashboard_period_snapshot = AsyncMock(\n        side_effect=[current, previous]\n    )\n    ticket_repository = cast(\n        TicketRepository,\n        SimpleNamespace(\n            get_dashboard_period_snapshot=get_dashboard_period_snapshot,\n            get_dashboard_operational_snapshot=AsyncMock(\n                return_value=operational\n            ),\n            list_assignee_options=AsyncMock(\n                return_value=[\n                    AssigneeFilterOption(external_id=91, name=None)\n                ]\n            ),\n        ),\n    )\n    customer_repository = cast(\n        CustomerRepository,\n        SimpleNamespace(\n            list_filter_options=AsyncMock(\n                return_value=[\n                    CustomerFilterOption(\n                        id=CUSTOMER_ID,\n                        requester_name=\"Cliente\",\n                        requester_email=\"cliente@example.com\",\n                    )\n                ]\n            )\n        ),\n    )\n    tag_repository = cast(\n        TagRepository,\n        SimpleNamespace(\n            list_filter_options=AsyncMock(\n                return_value=[TagFilterOption(id=TAG_ID, name=\"dns\")]\n            )\n        ),\n    )\n""",
    )

    replace_once(
        path,
        """    assert ticket_repository.get_dashboard_period_snapshot.await_count == 2\n    previous_filters = ticket_repository.get_dashboard_period_snapshot.await_args_list[1].args[0]\n    assert previous_filters.to_at < output.scope.from_at\n""",
        """    assert get_dashboard_period_snapshot.await_count == 2\n    previous_filters = cast(\n        AnalyticsFilters,\n        get_dashboard_period_snapshot.await_args_list[1].args[0],\n    )\n    assert previous_filters.to_at is not None\n    assert output.scope.from_at is not None\n    assert previous_filters.to_at < output.scope.from_at\n""",
    )

    replace_once(
        path,
        """    repository = SimpleNamespace(\n        page_customer_analytics=AsyncMock(\n""",
        """    repository = cast(\n        TicketRepository,\n        SimpleNamespace(\n            page_customer_analytics=AsyncMock(\n""",
    )

    replace_once(
        path,
        """            )\n        )\n    )\n\n    output = await ListCustomerMetrics(repository).execute(CustomerMetricsInput())\n""",
        """            )\n        )\n        ),\n    )\n\n    output = await ListCustomerMetrics(repository).execute(CustomerMetricsInput())\n""",
    )


def patch_pyproject() -> None:
    path = ROOT / "pyproject.toml"
    content = path.read_text(encoding="utf-8")
    config = """\n[tool.pyright]\npythonVersion = \"3.14\"\ntypeCheckingMode = \"standard\"\ninclude = [\"src\", \"tests\"]\n"""
    if "[tool.pyright]" not in content:
        path.write_text(content.rstrip() + "\n" + config, encoding="utf-8")


def main() -> None:
    patch_repositories()
    patch_tests()
    patch_pyproject()


if __name__ == "__main__":
    main()
