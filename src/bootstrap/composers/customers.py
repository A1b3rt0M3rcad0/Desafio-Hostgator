from src.application.use_cases.add_customer import AddCustomer
from src.application.use_cases.delete_customer import DeleteCustomer
from src.application.use_cases.get_customer import GetCustomer
from src.application.use_cases.list_customers import ListCustomers
from src.application.use_cases.update_customer import UpdateCustomer
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.repositories import SqlAlchemyCustomerRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.add_customer_controller import AddCustomerController
from src.presentation.http.controllers.delete_customer_controller import DeleteCustomerController
from src.presentation.http.controllers.get_customer_controller import GetCustomerController
from src.presentation.http.controllers.list_customers_controller import ListCustomersController
from src.presentation.http.controllers.update_customer_controller import UpdateCustomerController


def add_customer_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyCustomerRepository(unit_of_work)
    use_case = AddCustomer(repository)
    controller = AddCustomerController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def get_customer_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyCustomerRepository(unit_of_work)
    use_case = GetCustomer(repository)
    controller = GetCustomerController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def update_customer_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyCustomerRepository(unit_of_work)
    use_case = UpdateCustomer(repository)
    controller = UpdateCustomerController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def delete_customer_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyCustomerRepository(unit_of_work)
    use_case = DeleteCustomer(repository)
    controller = DeleteCustomerController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def list_customers_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyCustomerRepository(unit_of_work)
    use_case = ListCustomers(repository)
    controller = ListCustomersController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)
