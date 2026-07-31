from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.responses import Response as FastAPIResponse

from src.presentation.http.schemas.response import Response


def adapt_response(response: Response) -> FastAPIResponse:
    headers = {key: str(value) for key, value in response.headers.items()}

    adapted: FastAPIResponse
    if response.body is None:
        adapted = FastAPIResponse(
            status_code=response.status_code,
            headers=headers,
        )
    else:
        adapted = JSONResponse(
            status_code=response.status_code,
            content=jsonable_encoder(response.body),
            headers=headers,
        )

    for cookie in response.cookies:
        if cookie.delete:
            adapted.delete_cookie(
                key=cookie.key,
                path=cookie.path,
                domain=cookie.domain,
                secure=cookie.secure,
                httponly=cookie.httponly,
                samesite=cookie.samesite,
            )
            continue
        adapted.set_cookie(
            key=cookie.key,
            value=cookie.value,
            max_age=cookie.max_age,
            path=cookie.path,
            domain=cookie.domain,
            secure=cookie.secure,
            httponly=cookie.httponly,
            samesite=cookie.samesite,
        )

    return adapted
