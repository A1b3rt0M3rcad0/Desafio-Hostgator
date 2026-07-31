from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.responses import Response as FastAPIResponse

from src.presentation.http.schemas.response import Response


def adapt_response(response: Response) -> FastAPIResponse:
    headers = {key: str(value) for key, value in response.headers.items()}

    if response.body is None:
        return FastAPIResponse(
            status_code=response.status_code,
            headers=headers,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=jsonable_encoder(response.body),
        headers=headers,
    )
