from src.infra.database.models import (
    AuthSession,
    Customer,
    SatisfactionRating,
    Tag,
    Ticket,
    TicketTag,
    User,
)


def test_database_models_eagerly_load_server_defaults() -> None:
    models = (
        User,
        AuthSession,
        Customer,
        Ticket,
        SatisfactionRating,
        Tag,
        TicketTag,
    )

    for model in models:
        assert model.__mapper__.eager_defaults is True
