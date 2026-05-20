import uuid
import enum
import re
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RESIDENT = "resident"
    TENANT = "tenant"
    SECURITY = "security"
    STAFF = "staff"


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
    role: UserRole = Field(UserRole.RESIDENT, description="admin, resident, tenant, security, staff")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError("Phone number must be in E.164 format (e.g. +919999999999)")
        return v


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    vehicle_number: str | None = None


class UserOut(UserBase):
    id: uuid.UUID
    is_active: bool
    vehicle_number: str | None = None
    created_at: datetime
    flats: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class OTPRequest(BaseModel):
    phone: str = Field(..., examples=["+919999999999"])

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError("Phone number must be in E.164 format (e.g. +919999999999)")
        return v


class OTPVerify(BaseModel):
    phone: str = Field(..., examples=["+919999999999"])
    otp: str = Field(..., examples=["123456"])

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError("Phone number must be in E.164 format (e.g. +919999999999)")
        return v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: uuid.UUID
