from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import TagEntity


class UpdateTagInput(BaseModel):
    tag_id: UUID
    name: str | None = None


class UpdateTagOutput(BaseModel):
    tag: TagEntity
