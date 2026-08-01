from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.bootstrap.composers.database import DATABASE_ENGINE
from src.bootstrap.security import AUTH_SETTINGS
from src.presentation.http.fastapi.exceptions import register_exception_handlers
from src.presentation.http.fastapi.routes import (
    analytics_router,
    auth_router,
    customers_router,
    satisfaction_ratings_router,
    tags_router,
    ticket_tags_router,
    tickets_router,
    users_router,
)
from src.presentation.http.fastapi.security import require_authenticated_request


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await DATABASE_ENGINE.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Customer Support Analysis API",
        version="0.3.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(AUTH_SETTINGS.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", AUTH_SETTINGS.csrf_header_name],
        expose_headers=["Content-Disposition", "Content-Length"],
        max_age=600,
    )

    register_exception_handlers(application)
    application.include_router(auth_router)

    protected_dependencies = [Depends(require_authenticated_request)]
    application.include_router(customers_router, dependencies=protected_dependencies)
    application.include_router(users_router, dependencies=protected_dependencies)
    application.include_router(tickets_router, dependencies=protected_dependencies)
    application.include_router(tags_router, dependencies=protected_dependencies)
    application.include_router(satisfaction_ratings_router, dependencies=protected_dependencies)
    application.include_router(ticket_tags_router, dependencies=protected_dependencies)
    application.include_router(analytics_router, dependencies=protected_dependencies)

    return application


app = create_app()
