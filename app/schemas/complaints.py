import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CommentCreate(BaseModel):
    comment: str = Field(..., min_length=1)
    attachment_url: str | None = None


class CommentOut(BaseModel):
    id: uuid.UUID
    complaint_id: uuid.UUID
    user_id: uuid.UUID
    comment: str
    attachment_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintCreate(BaseModel):
    flat_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5)
    category: str = Field("other", description="plumbing, electricity, security, lift, housekeeping, parking, other")
    priority: str = Field("medium", description="low, medium, high, emergency")
    attachment_url: str | None = None


class ComplaintUpdate(BaseModel):
    status: str | None = Field(None, description="open, assigned, in_progress, resolved, closed")
    priority: str | None = Field(None, description="low, medium, high, emergency")
    assigned_to_id: uuid.UUID | None = None


class ComplaintOut(BaseModel):
    id: uuid.UUID
    flat_id: uuid.UUID
    raised_by_id: uuid.UUID
    title: str
    description: str
    category: str
    priority: str
    status: str
    assigned_to_id: uuid.UUID | None
    attachment_url: str | None
    created_at: datetime
    updated_at: datetime
    
    comments: list[CommentOut] = []

    model_config = ConfigDict(from_attributes=True)
