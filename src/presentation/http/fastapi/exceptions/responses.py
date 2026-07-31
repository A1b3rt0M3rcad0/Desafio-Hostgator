from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"error": error}),
    )
