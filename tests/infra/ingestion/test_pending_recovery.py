import asyncio
from types import SimpleNamespace

from src.infra.ingestion.schemas import BatchIngestionResult, TicketSourceRecord
from src.infra.workers.ticket_ingestion import runtime as runtime_module


def source_ticket() -> TicketSourceRecord:
    return TicketSourceRecord.model_validate(
        {
            "ticket_id": 100001,
            "subject": "Pending ticket",
            "description": "Description",
            "status": "open",
            "priority": "normal",
            "requester_id": 40000,
            "requester_name": "Customer",
            "requester_email": "customer@example.com",
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
            "tags": ["support"],
        }
    )


def test_pending_payload_round_trip_is_json_safe() -> None:
    record = source_ticket()

    restored = TicketSourceRecord.model_validate(record.model_dump(mode="json"))

    assert restored == record


def test_worker_prioritizes_recoverable_pending_before_source(monkeypatch) -> None:
    events: list[str] = []
    record = source_ticket()

    class FakeUnitOfWork:
        def __init__(self, engine) -> None:
            self.engine = engine

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class FakeControlRepository:
        def __init__(self, unit_of_work) -> None:
            pass

        async def get_worker_control(self, *, for_update=False):
            return SimpleNamespace(
                enabled=True,
                source_version="source-v1",
                cursor_position=175,
            )

        async def mark_processing(self) -> None:
            events.append("processing")

        async def complete_pending_batch(self) -> None:
            events.append("pending-complete")

    class FakeIngestionRepository:
        def __init__(self, unit_of_work) -> None:
            pass

        async def load_resolvable_pending(self, limit: int):
            assert limit == 25
            events.append("pending-loaded")
            return [record]

        async def synchronize_batch(self, records, **kwargs):
            assert records == [record]
            assert kwargs["queue_unresolved"] is False
            assert kwargs["recovered"] is True
            events.append("pending-synchronized")
            return BatchIngestionResult(
                received=1,
                created=1,
                updated=0,
                unchanged=0,
                unmatched=0,
                conflicted=0,
                recovered=1,
            )

    class SourceMustNotBeRead:
        def current_version(self):
            raise AssertionError(
                "Source must not be read while pending is recoverable"
            )

    monkeypatch.setattr(runtime_module, "UnitOfWork", FakeUnitOfWork)
    monkeypatch.setattr(
        runtime_module,
        "SqlAlchemyIngestionControlRepository",
        FakeControlRepository,
    )
    monkeypatch.setattr(
        runtime_module,
        "SqlAlchemyTicketIngestionRepository",
        FakeIngestionRepository,
    )

    worker = runtime_module.TicketIngestionWorker(
        engine=object(),
        source_repository=SourceMustNotBeRead(),
        settings=SimpleNamespace(
            batch_size=25,
            interval_seconds=30,
            control_poll_seconds=2,
        ),
    )

    asyncio.run(worker._process_next_batch())

    assert events == [
        "processing",
        "pending-loaded",
        "pending-synchronized",
        "pending-complete",
    ]
