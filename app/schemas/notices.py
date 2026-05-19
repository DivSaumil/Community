import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PollOptionCreate(BaseModel):
    option_text: str = Field(..., max_length=200)


class PollOptionOut(BaseModel):
    id: uuid.UUID
    option_text: str
    vote_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class NoticeCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=5)
    type: str = Field("general", description="general, emergency, event, poll")
    expires_at: datetime | None = None
    poll_options: list[str] | None = Field(None, description="Only required if type is 'poll'")


class NoticeOut(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    type: str
    created_by_id: uuid.UUID
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    
    poll_options: list[PollOptionOut] = []

    model_config = ConfigDict(from_attributes=True)


class VoteCreate(BaseModel):
    option_id: uuid.UUID


class VoteOut(BaseModel):
    id: uuid.UUID
    notice_id: uuid.UUID
    option_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
