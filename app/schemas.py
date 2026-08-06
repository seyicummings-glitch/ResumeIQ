from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    role: str
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


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


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