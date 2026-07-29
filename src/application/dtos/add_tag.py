from pydantic import BaseModel

from src.domain.entities import TagEntity


class AddTagInput(BaseModel):
    name: str


class AddTagOutput(BaseModel):
    tag: TagEntity
