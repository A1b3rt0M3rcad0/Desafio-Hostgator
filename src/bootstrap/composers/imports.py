from src.application.use_cases.imports import SyncTicketsFromMock
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.imports import SqlAlchemyTicketImportRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.imports import SyncTicketsFromMockController


def sync_tickets_from_mock_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketImportRepository(unit_of_work)
    controller = SyncTicketsFromMockController(SyncTicketsFromMock(repository))
    return TransactionalHandler(unit_of_work, controller.handle)
