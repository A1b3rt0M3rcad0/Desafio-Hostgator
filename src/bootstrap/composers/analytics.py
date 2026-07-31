from collections.abc import Callable
from typing import Any

from src.application.use_cases.analytics import (
    ExportMetricsReport,
    ExportRawReport,
    GetDashboardOverview,
    GetReportCatalog,
    ListCustomerMetrics,
    PreviewRawReport,
)
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.dashboard_workspace import DashboardWorkspaceQueryRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.infra.reports.writers import DefaultReportWriterFactory
from src.presentation.http.controllers.analytics import (
    ExportMetricsReportController,
    ExportRawReportController,
    GetDashboardOverviewController,
    GetReportCatalogController,
    ListCustomerMetricsController,
    PreviewRawReportController,
)


def _repository() -> tuple[UnitOfWork, DashboardWorkspaceQueryRepository]:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    return unit_of_work, DashboardWorkspaceQueryRepository(unit_of_work)


def get_dashboard_overview_composer() -> TransactionalHandler:
    unit_of_work, repository = _repository()
    controller = GetDashboardOverviewController(GetDashboardOverview(repository))
    return TransactionalHandler(unit_of_work, controller.handle)


def list_customer_metrics_composer() -> TransactionalHandler:
    unit_of_work, repository = _repository()
    controller = ListCustomerMetricsController(ListCustomerMetrics(repository))
    return TransactionalHandler(unit_of_work, controller.handle)


def get_report_catalog_composer() -> Callable[[Any], Any]:
    return GetReportCatalogController(GetReportCatalog()).handle


def preview_raw_report_composer() -> TransactionalHandler:
    unit_of_work, repository = _repository()
    controller = PreviewRawReportController(PreviewRawReport(repository))
    return TransactionalHandler(unit_of_work, controller.handle)


def export_raw_report_composer() -> TransactionalHandler:
    unit_of_work, repository = _repository()
    writer_factory = DefaultReportWriterFactory()
    controller = ExportRawReportController(ExportRawReport(repository, writer_factory))
    return TransactionalHandler(unit_of_work, controller.handle)


def export_metrics_report_composer() -> TransactionalHandler:
    unit_of_work, repository = _repository()
    writer_factory = DefaultReportWriterFactory()
    controller = ExportMetricsReportController(
        ExportMetricsReport(repository, writer_factory)
    )
    return TransactionalHandler(unit_of_work, controller.handle)
