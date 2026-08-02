#!/usr/bin/env python3
"""Seed the canonical demo customers used by data/tickets.json.

The seed is idempotent and intended only for local demonstration. Disable it by
setting DEMO_SEED_ENABLED=false in environments that already own their customer
base.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, func, or_, select
from sqlalchemy.orm import Session

from src.infra.database.models import Customer

CUSTOMERS_PATH = Path(
    os.getenv("DEMO_CUSTOMERS_PATH", "/app/data/customers_seed.json")
)


def is_enabled() -> bool:
    return os.getenv("DEMO_SEED_ENABLED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def load_customers() -> list[dict[str, object]]:
    payload = json.loads(CUSTOMERS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("DEMO_CUSTOMERS_PATH must contain a JSON list")
    return payload


def main() -> int:
    if not is_enabled():
        print("Demo customer seed disabled")
        return 0

    database_url = os.getenv("MYSQL_URL_CONNECTION_SEED") or os.getenv(
        "MYSQL_URL_CONNECTION_MIGRATIONS"
    )
    if not database_url:
        raise RuntimeError(
            "MYSQL_URL_CONNECTION_SEED or MYSQL_URL_CONNECTION_MIGRATIONS is required"
        )

    customers = load_customers()
    engine = create_engine(database_url, pool_pre_ping=True)
    inserted = 0
    updated = 0

    try:
        with Session(engine) as session:
            for raw in customers:
                external_id = int(raw["external_requester_id"])
                name = str(raw["requester_name"]).strip()
                email = str(raw["requester_email"]).strip().lower()
                customer = session.scalar(
                    select(Customer).where(
                        or_(
                            Customer.external_requester_id == external_id,
                            func.lower(Customer.requester_email) == email,
                        )
                    )
                )
                if customer is None:
                    session.add(
                        Customer(
                            external_requester_id=external_id,
                            requester_name=name,
                            requester_email=email,
                        )
                    )
                    inserted += 1
                else:
                    customer.external_requester_id = external_id
                    customer.requester_name = name
                    customer.requester_email = email
                    updated += 1
            session.commit()
    finally:
        engine.dispose()

    print(
        f"Demo customer seed completed: total={len(customers)} "
        f"inserted={inserted} updated={updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
