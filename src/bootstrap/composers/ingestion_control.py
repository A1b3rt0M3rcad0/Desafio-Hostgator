from src.application.use_cases.ingestion_control import (
    GetIngestionControl,
    UpdateIngestionControl,
)
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.repositories import SqlAlchemyTicketRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.ingestion_control import (
    GetIngestionControlController,
    UpdateIngestionControlController,
)


def get_ingestion_control_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = GetIngestionControl(repository)
    controller = GetIngestionControlController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def update_ingestion_control_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = UpdateIngestionControl(repository)
    controller = UpdateIngestionControlController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)
