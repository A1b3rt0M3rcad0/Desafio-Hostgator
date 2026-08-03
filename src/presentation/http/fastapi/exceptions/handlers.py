import logging
from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from src.presentation.http.fastapi.exceptions.responses import error_response


LOGGER = logging.getLogger(__name__)


def _exception_info(
    exception: BaseException,
) -> tuple[type[BaseException], BaseException, TracebackType | None]:
    return type(exception), exception, exception.__traceback__


def _validation_details(
    errors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in errors
    ]


async def http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
) -> Response:
    detail = exception.detail
    message = detail if isinstance(detail, str) else "The request could not be completed."
    details = None if isinstance(detail, str) else detail

    return error_response(
        status_code=exception.status_code,
        code="http_error",
        message=message,
        details=details,
    )


async def request_validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
) -> Response:
    return error_response(
        status_code=422,
        code="request_validation_error",
        message="The request contains invalid data.",
        details=_validation_details(exception.errors()),
    )


async def pydantic_validation_exception_handler(
    request: Request,
    exception: ValidationError,
) -> Response:
    return error_response(
        status_code=422,
        code="validation_error",
        message="The provided data could not be processed.",
        details=_validation_details(exception.errors()),
    )


async def integrity_exception_handler(
    request: Request,
    exception: IntegrityError,
) -> Response:
    LOGGER.warning(
        "Database integrity violation",
        exc_info=_exception_info(exception),
        extra={"method": request.method, "path": request.url.path},
    )

    return error_response(
        status_code=409,
        code="resource_conflict",
        message="The operation conflicts with the current resource state.",
    )


async def database_exception_handler(
    request: Request,
    exception: SQLAlchemyError,
) -> Response:
    LOGGER.error(
        "Database operation failed",
        exc_info=_exception_info(exception),
        extra={"method": request.method, "path": request.url.path},
    )

    return error_response(
        status_code=500,
        code="database_error",
        message="The database operation could not be completed.",
    )


async def unexpected_exception_handler(
    request: Request,
    exception: Exception,
) -> Response:
    LOGGER.error(
        "Unexpected application error",
        exc_info=_exception_info(exception),
        extra={"method": request.method, "path": request.url.path},
    )

    return error_response(
        status_code=500,
        code="internal_server_error",
        message="An unexpected internal error occurred.",
    )
