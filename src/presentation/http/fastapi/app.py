from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.bootstrap.composers.database import DATABASE_ENGINE
from src.presentation.http.fastapi.exceptions import register_exception_handlers
from src.presentation.http.fastapi.routes import (
    customers_router,
    satisfaction_ratings_router,
    tags_router,
    ticket_tags_router,
    tickets_router,
    users_router,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await DATABASE_ENGINE.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Customer Support Analysis API",
        version="0.1.0",
        lifespan=lifespan,
    )

    register_exception_handlers(application)
    application.include_router(customers_router)
    application.include_router(users_router)
    application.include_router(tickets_router)
    application.include_router(tags_router)
    application.include_router(satisfaction_ratings_router)
    application.include_router(ticket_tags_router)

    return application


app = create_app()
