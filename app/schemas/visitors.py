import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class VisitorPassCreate(BaseModel):
    flat_id: uuid.UUID
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    visitor_type: str = Field("guest", description="guest, delivery, service, other")
    vehicle_number: str | None = Field(None, max_length=20)
    expected_arrival: datetime
    # We can automatically set valid_until or accept it
    valid_until: datetime | None = None


class VisitorPassOut(BaseModel):
    id: uuid.UUID
    flat_id: uuid.UUID
    resident_id: uuid.UUID
    name: str
    phone: str
    visitor_type: str
    pass_code: str
    vehicle_number: str | None
    expected_arrival: datetime
    valid_until: datetime
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VisitorLogCreate(BaseModel):
    # For logs created with an active passcode
    pass_code: str | None = None
    
    # Optional fields if walk-in entry (not pre-approved)
    flat_id: uuid.UUID | None = None
    name: str | None = None
    phone: str | None = None
    visitor_type: str = "guest"
    vehicle_number: str | None = None
    purpose: str | None = None


class VisitorLogOut(BaseModel):
    id: uuid.UUID
    visitor_pass_id: uuid.UUID | None
    flat_id: uuid.UUID
    name: str
    phone: str
    visitor_type: str
    vehicle_number: str | None
    purpose: str | None
    entry_time: datetime
    exit_time: datetime | None
    entered_gate_by_id: uuid.UUID
    exited_gate_by_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyHelpCreate(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    role: str = Field(..., description="Maid, Driver, Cook, Gardener, etc.")
    flat_ids: list[uuid.UUID] = []


class DailyHelpCreateByResident(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    role: str = Field(..., description="Maid, Driver, Cook, Gardener, etc.")


class DailyHelpOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    role: str
    pass_code: str
    is_active: bool
    created_at: datetime
    
    flats: list[str] = []

    model_config = ConfigDict(from_attributes=True)
