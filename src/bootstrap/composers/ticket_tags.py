from src.application.use_cases.add_ticket_tag import AddTicketTag
from src.application.use_cases.delete_ticket_tag import DeleteTicketTag
from src.application.use_cases.list_tickets_by_tags import ListTicketsByTags
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.repositories import (
    SqlAlchemyTicketRepository,
    SqlAlchemyTicketTagRepository,
)
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.add_ticket_tag_controller import AddTicketTagController
from src.presentation.http.controllers.delete_ticket_tag_controller import (
    DeleteTicketTagController,
)
from src.presentation.http.controllers.list_tickets_by_tags_controller import (
    ListTicketsByTagsController,
)


def add_ticket_tag_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketTagRepository(unit_of_work)
    use_case = AddTicketTag(repository)
    controller = AddTicketTagController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def delete_ticket_tag_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketTagRepository(unit_of_work)
    use_case = DeleteTicketTag(repository)
    controller = DeleteTicketTagController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def list_tickets_by_tags_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = ListTicketsByTags(repository)
    controller = ListTicketsByTagsController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)
