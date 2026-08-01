from src.presentation.http.fastapi.routes.analytics import router as analytics_router
from src.presentation.http.fastapi.routes.exports import router as exports_router


def _paths(router: object) -> set[str]:
    return {
        path
        for route in router.routes
        if (path := getattr(route, "path", None)) is not None
    }


def test_export_routes_replace_manual_import_and_legacy_report_routes() -> None:
    export_paths = _paths(exports_router)
    analytics_paths = _paths(analytics_router)

    assert export_paths == {
        "/exports/catalog",
        "/exports/data/preview",
        "/exports/data/download",
        "/exports/metrics/download",
    }

    all_paths = export_paths | analytics_paths
    assert "/imports/tickets/sync" not in all_paths
    assert not any(path.startswith("/reports/") for path in all_paths)
