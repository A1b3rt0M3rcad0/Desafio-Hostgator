from src.application.use_cases.add_satisfaction_rating import AddSatisfactionRating
from src.application.use_cases.delete_satisfaction_rating import DeleteSatisfactionRating
from src.application.use_cases.get_satisfaction_rating import GetSatisfactionRating
from src.application.use_cases.list_satisfaction_ratings import ListSatisfactionRatings
from src.application.use_cases.update_satisfaction_rating import UpdateSatisfactionRating
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.infra.database.repositories import SqlAlchemySatisfactionRatingRepository
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.add_satisfaction_rating_controller import (
    AddSatisfactionRatingController,
)
from src.presentation.http.controllers.delete_satisfaction_rating_controller import (
    DeleteSatisfactionRatingController,
)
from src.presentation.http.controllers.get_satisfaction_rating_controller import (
    GetSatisfactionRatingController,
)
from src.presentation.http.controllers.list_satisfaction_ratings_controller import (
    ListSatisfactionRatingsController,
)
from src.presentation.http.controllers.update_satisfaction_rating_controller import (
    UpdateSatisfactionRatingController,
)


def add_satisfaction_rating_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemySatisfactionRatingRepository(unit_of_work)
    use_case = AddSatisfactionRating(repository)
    controller = AddSatisfactionRatingController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def get_satisfaction_rating_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemySatisfactionRatingRepository(unit_of_work)
    use_case = GetSatisfactionRating(repository)
    controller = GetSatisfactionRatingController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def update_satisfaction_rating_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemySatisfactionRatingRepository(unit_of_work)
    use_case = UpdateSatisfactionRating(repository)
    controller = UpdateSatisfactionRatingController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def delete_satisfaction_rating_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemySatisfactionRatingRepository(unit_of_work)
    use_case = DeleteSatisfactionRating(repository)
    controller = DeleteSatisfactionRatingController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def list_satisfaction_ratings_composer() -> TransactionalHandler:
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemySatisfactionRatingRepository(unit_of_work)
    use_case = ListSatisfactionRatings(repository)
    controller = ListSatisfactionRatingsController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)
