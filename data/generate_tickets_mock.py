#!/usr/bin/env python3
"""Generate the static ticket source consumed by the infrastructure worker.

The complete scenario catalog remains in ``mock/generate_tickets_mock.py``. This
entrypoint fixes the challenge fixture at 1 August 2026, prevents future timestamps
and writes ``data/tickets.json`` with 10,000 deterministic records distributed over
the preceding two years. The historical range keeps 7, 30 and 90-day dashboard
windows useful at the start of August.
"""

from __future__ import annotations

import argparse
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_GENERATOR = ROOT / "mock" / "generate_tickets_mock.py"
DEFAULT_OUTPUT = Path(__file__).with_name("tickets.json")
DEFAULT_ANCHOR = "2026-08-01T05:30:00Z"
DEFAULT_COUNT = 10_000
DEFAULT_CUSTOMERS = 500
DEFAULT_START_ID = 100_001
DEFAULT_SEED = "hostgator-challenge-august-2026"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "hostgator_ticket_generator",
        SOURCE_GENERATOR,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {SOURCE_GENERATOR}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_anchor(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def clamp_iso8601(
    generator: ModuleType,
    value: str | None,
    anchor: datetime,
) -> str | None:
    if value is None:
        return None
    parsed = generator.parse_iso8601(value)
    return generator.isoformat_z(min(parsed, anchor))


def cap_future_timestamps(
    generator: ModuleType,
    tickets: list[dict[str, Any]],
    anchor: datetime,
) -> None:
    for ticket in tickets:
        ticket["updated_at"] = clamp_iso8601(
            generator,
            ticket["updated_at"],
            anchor,
        )
        ticket["first_response_at"] = clamp_iso8601(
            generator,
            ticket["first_response_at"],
            anchor,
        )

        rating = ticket.get("satisfaction_rating")
        if rating:
            rating["offered_at"] = clamp_iso8601(
                generator,
                rating.get("offered_at"),
                anchor,
            )
            rating["rated_at"] = clamp_iso8601(
                generator,
                rating.get("rated_at"),
                anchor,
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera data/tickets.json para o desafio HostGator.",
    )
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS)
    parser.add_argument("--start-id", type=int, default=DEFAULT_START_ID)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--anchor", default=DEFAULT_ANCHOR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Grava JSON indentado; por padrão o arquivo é compacto.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generator = load_generator()
    anchor = parse_anchor(args.anchor)

    tickets = generator.generate_dataset(
        count=args.count,
        customer_count=args.customers,
        start_id=args.start_id,
        master_seed=args.seed,
        anchor_at=anchor,
    )
    cap_future_timestamps(generator, tickets, anchor)

    summary = generator.validate_dataset(
        tickets=tickets,
        expected_count=args.count,
        customer_count=args.customers,
    )
    digest = generator.write_json(
        output_path=args.output,
        tickets=tickets,
        compact=not args.pretty,
    )

    created_values = [generator.parse_iso8601(item["created_at"]) for item in tickets]
    updated_values = [generator.parse_iso8601(item["updated_at"]) for item in tickets]
    august_tickets = sum(
        value.year == 2026 and value.month == 8
        for value in created_values
    )
    last_30_days = sum(
        value >= anchor - generator.timedelta(days=30)
        for value in created_values
    )

    print(f"Arquivo: {args.output.resolve()}")
    print(f"SHA-256: {digest}")
    print(f"Âncora: {generator.isoformat_z(anchor)}")
    print(f"Tickets: {summary['tickets']}")
    print(f"Clientes: {summary['customers']}")
    print(f"Criados em agosto/2026: {august_tickets}")
    print(f"Criados nos últimos 30 dias: {last_30_days}")
    print(f"Menor created_at: {generator.isoformat_z(min(created_values))}")
    print(f"Maior created_at: {generator.isoformat_z(max(created_values))}")
    print(f"Maior updated_at: {generator.isoformat_z(max(updated_values))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
