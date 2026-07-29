from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import TagEntity


class GetTagInput(BaseModel):
    tag_id: UUID


class GetTagOutput(BaseModel):
    tag: TagEntity | None
