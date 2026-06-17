import uuid
import enum
import re
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr


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
    email: EmailStr = Field(..., examples=["resident@example.com"])
    name: str = Field(..., max_length=100, examples=["Rahul Sharma"])
    role: UserRole = Field(UserRole.RESIDENT, description="admin, resident, tenant, security, staff")


class UserCreate(UserBase):
    block: str | None = None
    flat_number: str | None = None
    vehicle_number: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    vehicle_number: str | None = None
    block: str | None = None
    flat_number: str | None = None


class UserRegister(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    role: UserRole = UserRole.RESIDENT
    block: str = Field(..., max_length=20)
    flat_number: str = Field(..., max_length=20)
    vehicle_number: str | None = None
    otp: str



class FamilyMemberCreate(BaseModel):
    name: str = Field(..., max_length=100, examples=["Sunita Sharma"])
    relation: str = Field(..., max_length=50, examples=["Spouse"])
    phone: str | None = Field(None, max_length=20, examples=["+91 98765 43210"])
    email: EmailStr | None = None


class FamilyMemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    relation: str
    phone: str | None = None
    email: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserOut(UserBase):
    id: uuid.UUID
    is_active: bool
    vehicle_number: str | None = None
    created_at: datetime
    flats: list[str] = []
    flats_detailed: list[FlatOut] = []
    family_members: list[FamilyMemberOut] = []

    model_config = ConfigDict(from_attributes=True)


class OTPRequest(BaseModel):
    email: EmailStr = Field(..., examples=["resident@example.com"])


class OTPVerify(BaseModel):
    email: EmailStr = Field(..., examples=["resident@example.com"])
    otp: str = Field(..., examples=["123456"])


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: uuid.UUID
