from src.application.use_cases.add_tag import AddTag
from src.application.use_cases.delete_tag import DeleteTag
from src.application.use_cases.get_tag import GetTag
from src.application.use_cases.list_tags import ListTags
from src.application.use_cases.update_tag import UpdateTag
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.repositories import SqlAlchemyTagRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.add_tag_controller import AddTagController
from src.presentation.http.controllers.delete_tag_controller import DeleteTagController
from src.presentation.http.controllers.get_tag_controller import GetTagController
from src.presentation.http.controllers.list_tags_controller import ListTagsController
from src.presentation.http.controllers.update_tag_controller import UpdateTagController


def add_tag_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTagRepository(unit_of_work)
    use_case = AddTag(repository)
    controller = AddTagController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def get_tag_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTagRepository(unit_of_work)
    use_case = GetTag(repository)
    controller = GetTagController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def update_tag_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTagRepository(unit_of_work)
    use_case = UpdateTag(repository)
    controller = UpdateTagController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def delete_tag_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTagRepository(unit_of_work)
    use_case = DeleteTag(repository)
    controller = DeleteTagController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def list_tags_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTagRepository(unit_of_work)
    use_case = ListTags(repository)
    controller = ListTagsController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)
