from src.presentation.http.fastapi.routes.analytics import router as analytics_router
from src.presentation.http.fastapi.routes.auth import router as auth_router
from src.presentation.http.fastapi.routes.customers import router as customers_router
from src.presentation.http.fastapi.routes.satisfaction_ratings import router as satisfaction_ratings_router
from src.presentation.http.fastapi.routes.tags import router as tags_router
from src.presentation.http.fastapi.routes.ticket_tags import router as ticket_tags_router
from src.presentation.http.fastapi.routes.tickets import router as tickets_router
from src.presentation.http.fastapi.routes.users import router as users_router

__all__ = [
    "analytics_router",
    "auth_router",
    "customers_router",
    "satisfaction_ratings_router",
    "tags_router",
    "ticket_tags_router",
    "tickets_router",
    "users_router",
]
