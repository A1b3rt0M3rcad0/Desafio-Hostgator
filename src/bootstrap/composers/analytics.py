from src.application.use_cases.analytics import GetDashboardOverview, ListCustomerMetrics
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.repositories import (
    SqlAlchemyCustomerRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyTicketRepository,
)
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.analytics import (
    GetDashboardOverviewController,
    ListCustomerMetricsController,
)


def get_dashboard_overview_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    ticket_repository = SqlAlchemyTicketRepository(unit_of_work)
    customer_repository = SqlAlchemyCustomerRepository(unit_of_work)
    tag_repository = SqlAlchemyTagRepository(unit_of_work)
    controller = GetDashboardOverviewController(
        GetDashboardOverview(
            ticket_repository=ticket_repository,
            customer_repository=customer_repository,
            tag_repository=tag_repository,
        )
    )
    return TransactionalHandler(unit_of_work, controller.handle)


def list_customer_metrics_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    ticket_repository = SqlAlchemyTicketRepository(unit_of_work)
    controller = ListCustomerMetricsController(
        ListCustomerMetrics(ticket_repository)
    )
    return TransactionalHandler(unit_of_work, controller.handle)
