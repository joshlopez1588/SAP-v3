from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = Field(min_length=1, max_length=255)
    invite_code: str = Field(min_length=4, max_length=50)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime


class RefreshResponse(TokenResponse):
    pass


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str
    role: str
    is_active: bool
    created_at: datetime


class InviteCreateRequest(BaseModel):
    email: EmailStr | None = None
    role: str = "analyst"
    expires_at: datetime | None = None


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    email: str | None
    role: str
    is_active: bool
    created_at: datetime
    expires_at: datetime | None
    used_at: datetime | None
