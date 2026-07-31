from src.application.use_cases.add_user import AddUser
from src.application.use_cases.delete_user import DeleteUser
from src.application.use_cases.get_user import GetUser
from src.application.use_cases.list_users import ListUsers
from src.application.use_cases.update_user import UpdateUser
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.bootstrap.security import PASSWORD_HASHER
from src.infra.database.repositories import (
    SqlAlchemyAuthSessionRepository,
    SqlAlchemyUserRepository,
)
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.add_user_controller import AddUserController
from src.presentation.http.controllers.delete_user_controller import DeleteUserController
from src.presentation.http.controllers.get_user_controller import GetUserController
from src.presentation.http.controllers.list_users_controller import ListUsersController
from src.presentation.http.controllers.update_user_controller import UpdateUserController


def add_user_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyUserRepository(unit_of_work)
    use_case = AddUser(repository, PASSWORD_HASHER)
    controller = AddUserController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def get_user_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyUserRepository(unit_of_work)
    use_case = GetUser(repository)
    controller = GetUserController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def update_user_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyUserRepository(unit_of_work)
    session_repository = SqlAlchemyAuthSessionRepository(unit_of_work)
    use_case = UpdateUser(repository, PASSWORD_HASHER, session_repository)
    controller = UpdateUserController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def delete_user_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyUserRepository(unit_of_work)
    use_case = DeleteUser(repository)
    controller = DeleteUserController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def list_users_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyUserRepository(unit_of_work)
    use_case = ListUsers(repository)
    controller = ListUsersController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)
