"""Auth-related Pydantic schemas."""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    plan: str
    api_key: Optional[str] = None
    plan_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: Optional[str] = None


class PlanUpdateRequest(BaseModel):
    plan: str  # 'pro' | 'developer'
    updated_by: str
    plan_expires_at: Optional[str] = None  # ISO 8601, null = 무제한
