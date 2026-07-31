from src.application.use_cases.add_ticket import AddTicket
from src.application.use_cases.delete_ticket import DeleteTicket
from src.application.use_cases.get_ticket import GetTicket
from src.application.use_cases.list_tickets import ListTickets
from src.application.use_cases.update_ticket import UpdateTicket
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.repositories import SqlAlchemyTicketRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.add_ticket_controller import AddTicketController
from src.presentation.http.controllers.delete_ticket_controller import DeleteTicketController
from src.presentation.http.controllers.get_ticket_controller import GetTicketController
from src.presentation.http.controllers.list_tickets_controller import ListTicketsController
from src.presentation.http.controllers.update_ticket_controller import UpdateTicketController


def add_ticket_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = AddTicket(repository)
    controller = AddTicketController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def get_ticket_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = GetTicket(repository)
    controller = GetTicketController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def update_ticket_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = UpdateTicket(repository)
    controller = UpdateTicketController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def delete_ticket_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = DeleteTicket(repository)
    controller = DeleteTicketController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def list_tickets_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = ListTickets(repository)
    controller = ListTicketsController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)
