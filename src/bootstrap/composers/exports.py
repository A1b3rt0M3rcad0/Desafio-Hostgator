from src.application.use_cases.exports import (
    ExportData,
    ExportMetrics,
    GetExportCatalog,
    PreviewDataExport,
)
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.analytics import SqlAlchemyAnalyticsQueryRepository
from src.infra.database.exports import SqlAlchemyDataExportRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.infra.reports import DefaultReportWriterFactory
from src.presentation.http.controllers.exports import (
    ExportDataController,
    ExportMetricsController,
    GetExportCatalogController,
    PreviewDataExportController,
)

_REPORT_WRITERS = DefaultReportWriterFactory()


def get_export_catalog_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyDataExportRepository(unit_of_work)
    controller = GetExportCatalogController(GetExportCatalog(repository))
    return TransactionalHandler(unit_of_work, controller.handle)


def preview_data_export_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyDataExportRepository(unit_of_work)
    controller = PreviewDataExportController(PreviewDataExport(repository))
    return TransactionalHandler(unit_of_work, controller.handle)


def export_data_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyDataExportRepository(unit_of_work)
    controller = ExportDataController(ExportData(repository, _REPORT_WRITERS))
    return TransactionalHandler(unit_of_work, controller.handle)


def export_metrics_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyAnalyticsQueryRepository(unit_of_work)
    controller = ExportMetricsController(ExportMetrics(repository, _REPORT_WRITERS))
    return TransactionalHandler(unit_of_work, controller.handle)
