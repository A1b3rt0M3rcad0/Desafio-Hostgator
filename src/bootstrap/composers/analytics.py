from src.application.use_cases.analytics import GetDashboardOverview, ListCustomerMetrics
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.analytics import SqlAlchemyAnalyticsQueryRepository
from src.infra.database.dashboard_workspace import DashboardWorkspaceQueryRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.analytics import (
    GetDashboardOverviewController,
    ListCustomerMetricsController,
)


def get_dashboard_overview_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = DashboardWorkspaceQueryRepository(unit_of_work)
    controller = GetDashboardOverviewController(GetDashboardOverview(repository))
    return TransactionalHandler(unit_of_work, controller.handle)


def list_customer_metrics_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyAnalyticsQueryRepository(unit_of_work)
    controller = ListCustomerMetricsController(ListCustomerMetrics(repository))
    return TransactionalHandler(unit_of_work, controller.handle)
