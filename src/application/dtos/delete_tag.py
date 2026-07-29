from uuid import UUID

from pydantic import BaseModel


class DeleteTagInput(BaseModel):
    tag_id: UUID


class DeleteTagOutput(BaseModel):
    success: bool
