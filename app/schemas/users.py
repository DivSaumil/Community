import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class FlatBase(BaseModel):
    block: str = Field(..., max_length=20, examples=["A", "B"])
    flat_number: str = Field(..., max_length=20, examples=["101", "1204"])


class FlatCreate(FlatBase):
    owner_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None


class FlatOut(FlatBase):
    id: uuid.UUID
    owner_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    phone: str = Field(..., max_length=20, examples=["+919999999999"])
    name: str = Field(..., max_length=100, examples=["Rahul Sharma"])
    role: str = Field("resident", description="admin, resident, tenant, security, staff")


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OTPRequest(BaseModel):
    phone: str = Field(..., examples=["+919999999999"])


class OTPVerify(BaseModel):
    phone: str = Field(..., examples=["+919999999999"])
    otp: str = Field(..., examples=["123456"])


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: uuid.UUID
