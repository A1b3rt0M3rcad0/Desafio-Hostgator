from typing import Any, Literal

from pydantic import BaseModel, Field


class ResponseCookie(BaseModel):
    key: str
    value: str = ""
    max_age: int | None = None
    path: str = "/"
    domain: str | None = None
    secure: bool = True
    httponly: bool = True
    samesite: Literal["lax", "strict", "none"] = "lax"
    delete: bool = False


class Response(BaseModel):
    status_code: int
    body: Any = None
    stream: Any = None
    headers: dict[str, Any] = Field(default_factory=dict)
    cookies: list[ResponseCookie] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
