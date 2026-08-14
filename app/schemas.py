import re

from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime


def validate_password_strength(password: str) -> str:
    """Shared by every schema that sets a new password (registration, password
    reset, change password) — never applied to UserLogin.password, since that
    would reject login attempts for existing accounts whose real password
    predates this policy. Mirrors the frontend's passwordSchema
    (src/lib/passwordValidation.js) — keep both in sync."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 20:
        raise ValueError("Password must be at most 20 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must include at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must include at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must include at least one number")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must include at least one special character")
    return password


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    role: str
    is_verified: bool
    created_at: datetime
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    target_role: str | None = None
    industry: str | None = None
    experience_level: str | None = None
    career_goals: str | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    target_role: str | None = None
    industry: str | None = None
    experience_level: str | None = None
    career_goals: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class RegisterResponse(BaseModel):
    """Registration no longer logs the user in directly — they must verify their
    email first (see app/routes/auth.py's register()/login()) — so this returns
    a status message instead of the created user. `verification_token` is only
    populated in the dev fallback where no SMTP is configured (mirrors
    PasswordResetRequest's `reset_token` dev fallback)."""

    message: str
    email: str
    verification_token: str | None = None


class EmailVerificationConfirm(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class JobDescriptionCreate(BaseModel):
    title: str | None = None
    content: str


class JobDescriptionResponse(BaseModel):
    id: int
    title: str | None = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True