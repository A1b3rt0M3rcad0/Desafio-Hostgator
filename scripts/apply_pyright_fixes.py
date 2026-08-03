from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if new in content:
        return
    if old not in content:
        raise RuntimeError(f"Expected block not found in {path}: {old[:100]!r}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


def patch_transactional_handler() -> None:
    path = ROOT / "src/application/contracts/transactional_handler.py"
    replace_once(
        path,
        'InputT = TypeVar("InputT")\nOutputT = TypeVar("OutputT")\n',
        'InputT = TypeVar("InputT", contravariant=True)\nOutputT = TypeVar("OutputT", covariant=True)\n',
    )


def patch_security() -> None:
    path = ROOT / "src/bootstrap/security.py"
    replace_once(
        path,
        "from typing import Literal\n",
        "from typing import Literal, cast\n",
    )
    replace_once(
        path,
        'COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()\nif COOKIE_SAMESITE not in {"lax", "strict", "none"}:\n    raise RuntimeError("AUTH_COOKIE_SAMESITE must be lax, strict or none.")\n',
        'cookie_samesite_value = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()\nif cookie_samesite_value not in {"lax", "strict", "none"}:\n    raise RuntimeError("AUTH_COOKIE_SAMESITE must be lax, strict or none.")\nCOOKIE_SAMESITE = cast(\n    Literal["lax", "strict", "none"],\n    cookie_samesite_value,\n)\n',
    )


def patch_repositories() -> None:
    path = ROOT / "src/infra/database/repositories.py"
    replace_once(
        path,
        "from typing import Any, overload\n",
        "from typing import Any, cast, overload\n",
    )
    replace_once(
        path,
        "from sqlalchemy.ext.asyncio import AsyncSession\n",
        "from sqlalchemy.engine import CursorResult\nfrom sqlalchemy.ext.asyncio import AsyncSession\n",
    )
    replace_once(
        path,
        """        result = await self._session.execute(\n            update(AuthSession)\n            .where(\n                AuthSession.user_id == user_id,\n                AuthSession.revoked_at.is_(None),\n            )\n            .values(revoked_at=now)\n        )\n        await self._session.flush()\n        return result.rowcount or 0\n""",
        """        result = cast(\n            CursorResult[Any],\n            await self._session.execute(\n                update(AuthSession)\n                .where(\n                    AuthSession.user_id == user_id,\n                    AuthSession.revoked_at.is_(None),\n                )\n                .values(revoked_at=now)\n            ),\n        )\n        await self._session.flush()\n        return result.rowcount or 0\n""",
    )


def patch_exception_handlers() -> None:
    path = ROOT / "src/presentation/http/fastapi/exceptions/handlers.py"
    replace_once(
        path,
        "import logging\nfrom types import TracebackType\nfrom typing import Any\n",
        "import logging\nfrom collections.abc import Mapping, Sequence\nfrom types import TracebackType\nfrom typing import Any\n",
    )
    replace_once(
        path,
        "def _validation_details(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:\n",
        "def _validation_details(\n    errors: Sequence[Mapping[str, Any]],\n) -> list[dict[str, Any]]:\n",
    )


def patch_exception_registry() -> None:
    path = ROOT / "src/presentation/http/fastapi/exceptions/registry.py"
    replace_once(
        path,
        "from fastapi import FastAPI\n",
        "from typing import cast\n\nfrom fastapi import FastAPI\n",
    )
    replace_once(
        path,
        "from starlette.exceptions import HTTPException as StarletteHTTPException\n",
        "from starlette.exceptions import HTTPException as StarletteHTTPException\nfrom starlette.types import ExceptionHandler\n",
    )
    for handler in (
        "http_exception_handler",
        "request_validation_exception_handler",
        "pydantic_validation_exception_handler",
        "integrity_exception_handler",
        "database_exception_handler",
        "unexpected_exception_handler",
    ):
        replace_once(
            path,
            f"        {handler},\n",
            f"        cast(ExceptionHandler, {handler}),\n",
        )


def patch_tests() -> None:
    path = ROOT / "tests/application/use_cases/test_analytics_use_cases.py"
    replace_once(
        path,
        "import asyncio\n",
        "import asyncio\nfrom datetime import datetime, timezone\n",
    )
    replace_once(
        path,
        '            from_at="2026-07-10T00:00:00Z",\n            to_at="2026-07-12T00:00:00Z",\n',
        "            from_at=datetime(2026, 7, 10, tzinfo=timezone.utc),\n            to_at=datetime(2026, 7, 12, tzinfo=timezone.utc),\n",
    )
    replace_once(
        path,
        """        SimpleNamespace(\n            page_customer_analytics=AsyncMock(\n            return_value=CustomerAnalyticsQueryPage(\n""",
        """        SimpleNamespace(\n            page_customer_analytics=AsyncMock(\n                return_value=CustomerAnalyticsQueryPage(\n""",
    )
    replace_once(
        path,
        """            )\n        )\n        ),\n    )\n\n    output = await ListCustomerMetrics(repository).execute(CustomerMetricsInput())\n""",
        """                )\n            ),\n        ),\n    )\n\n    output = await ListCustomerMetrics(repository).execute(CustomerMetricsInput())\n""",
    )


def main() -> None:
    patch_transactional_handler()
    patch_security()
    patch_repositories()
    patch_exception_handlers()
    patch_exception_registry()
    patch_tests()


if __name__ == "__main__":
    main()
