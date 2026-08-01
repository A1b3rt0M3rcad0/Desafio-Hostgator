from src.presentation.http.fastapi.app import create_app


def test_export_routes_replace_manual_import_and_legacy_report_routes() -> None:
    paths = {route.path for route in create_app().routes}

    assert {
        "/exports/catalog",
        "/exports/data/preview",
        "/exports/data/download",
        "/exports/metrics/download",
    }.issubset(paths)

    assert "/imports/tickets/sync" not in paths
    assert not any(path.startswith("/reports/") for path in paths)
