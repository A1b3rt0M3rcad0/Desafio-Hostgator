from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ExceptionHandler

from src.presentation.http.fastapi.exceptions.handlers import (
    database_exception_handler,
    http_exception_handler,
    integrity_exception_handler,
    pydantic_validation_exception_handler,
    request_validation_exception_handler,
    unexpected_exception_handler,
)


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(
        StarletteHTTPException,
        cast(ExceptionHandler, http_exception_handler),
    )
    application.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, request_validation_exception_handler),
    )
    application.add_exception_handler(
        ValidationError,
        cast(ExceptionHandler, pydantic_validation_exception_handler),
    )
    application.add_exception_handler(
        IntegrityError,
        cast(ExceptionHandler, integrity_exception_handler),
    )
    application.add_exception_handler(
        SQLAlchemyError,
        cast(ExceptionHandler, database_exception_handler),
    )
    application.add_exception_handler(
        Exception,
        cast(ExceptionHandler, unexpected_exception_handler),
    )
