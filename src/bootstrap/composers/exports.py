from src.application.use_cases.exports import (
    ExportData,
    ExportMetrics,
    GetExportCatalog,
    PreviewDataExport,
)
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.repositories import (
    SqlAlchemyCustomerRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyTicketRepository,
)
from src.infra.database.streaming_transactional_handler import (
    StreamingTransactionalHandler,
)
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
    ticket_repository = SqlAlchemyTicketRepository(unit_of_work)
    customer_repository = SqlAlchemyCustomerRepository(unit_of_work)
    tag_repository = SqlAlchemyTagRepository(unit_of_work)
    controller = GetExportCatalogController(
        GetExportCatalog(
            ticket_repository=ticket_repository,
            customer_repository=customer_repository,
            tag_repository=tag_repository,
        )
    )
    return TransactionalHandler(unit_of_work, controller.handle)


def preview_data_export_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    ticket_repository = SqlAlchemyTicketRepository(unit_of_work)
    controller = PreviewDataExportController(
        PreviewDataExport(ticket_repository)
    )
    return TransactionalHandler(unit_of_work, controller.handle)


def export_data_composer() -> StreamingTransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    ticket_repository = SqlAlchemyTicketRepository(unit_of_work)
    controller = ExportDataController(
        ExportData(ticket_repository, _REPORT_WRITERS)
    )
    return StreamingTransactionalHandler(unit_of_work, controller.handle)


def export_metrics_composer() -> StreamingTransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    ticket_repository = SqlAlchemyTicketRepository(unit_of_work)
    controller = ExportMetricsController(
        ExportMetrics(ticket_repository, _REPORT_WRITERS)
    )
    return StreamingTransactionalHandler(unit_of_work, controller.handle)
