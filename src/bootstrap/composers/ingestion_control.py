from src.application.use_cases.ingestion_control import (
    GetIngestionControl,
    IngestTicketBatch,
    UpdateIngestionControl,
)
from src.infra.database.repositories import (
    SqlAlchemyCustomerRepository,
    SqlAlchemySatisfactionRatingRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyTicketRepository,
    SqlAlchemyTicketTagRepository,
)
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.ingestion_control import (
    GetIngestionControlController,
    UpdateIngestionControlController,
)


def get_ingestion_control_composer() -> TransactionalHandler:
    from src.bootstrap.composers.database import DATABASE_ENGINE

    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = GetIngestionControl(repository)
    controller = GetIngestionControlController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def update_ingestion_control_composer() -> TransactionalHandler:
    from src.bootstrap.composers.database import DATABASE_ENGINE

    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    repository = SqlAlchemyTicketRepository(unit_of_work)
    use_case = UpdateIngestionControl(repository)
    controller = UpdateIngestionControlController(use_case)
    return TransactionalHandler(unit_of_work, controller.handle)


def ingest_ticket_batch_composer(
    unit_of_work: UnitOfWork,
) -> IngestTicketBatch:
    return IngestTicketBatch(
        customer_repository=SqlAlchemyCustomerRepository(unit_of_work),
        ticket_repository=SqlAlchemyTicketRepository(unit_of_work),
        tag_repository=SqlAlchemyTagRepository(unit_of_work),
        ticket_tag_repository=SqlAlchemyTicketTagRepository(unit_of_work),
        satisfaction_repository=SqlAlchemySatisfactionRatingRepository(
            unit_of_work
        ),
    )
