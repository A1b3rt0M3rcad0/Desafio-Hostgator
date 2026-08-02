from __future__ import annotations

import asyncio
import logging
import signal

from src.infra.workers.ticket_ingestion.engine import get_worker_engine
from src.infra.workers.ticket_ingestion.runtime import TicketIngestionWorker
from src.infra.workers.ticket_ingestion.settings import WorkerSettings


async def async_main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = WorkerSettings.from_env()
    engine = get_worker_engine(settings)
    worker = TicketIngestionWorker(engine=engine, settings=settings)

    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, worker.request_shutdown)
        except NotImplementedError:
            pass

    try:
        await worker.run()
    finally:
        await engine.dispose()
        get_worker_engine.cache_clear()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
