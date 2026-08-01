from datetime import datetime

from pydantic import BaseModel


class IngestionControlState(BaseModel):
    enabled: bool
    worker_state: str
    cursor_position: int
    last_heartbeat_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None


class GetIngestionControlInput(BaseModel):
    pass


class GetIngestionControlOutput(BaseModel):
    control: IngestionControlState


class UpdateIngestionControlInput(BaseModel):
    enabled: bool


class UpdateIngestionControlOutput(BaseModel):
    control: IngestionControlState
