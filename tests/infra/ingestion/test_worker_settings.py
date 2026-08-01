from src.infra.workers.ticket_ingestion.settings import WorkerSettings


def test_worker_defaults_are_one_batch_of_25_every_30_seconds(monkeypatch) -> None:
    monkeypatch.setenv(
        "MYSQL_URL_CONNECTION_WORKER",
        "mysql+aiomysql://root:password@db:3306/test",
    )
    monkeypatch.delenv("WORKER_BATCH_SIZE", raising=False)
    monkeypatch.delenv("WORKER_INTERVAL_SECONDS", raising=False)

    settings = WorkerSettings.from_env()

    assert settings.batch_size == 25
    assert settings.interval_seconds == 30
