import re

from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from email_validator import validate_email as check_email_deliverable, EmailNotValidError


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


# Known disposable/temporary-inbox providers — rejected at registration so an
# account can't be created against a mailbox that's designed to self-destruct.
# This is on top of, not instead of, the email verification link: a disposable
# inbox could otherwise still receive and click that link before expiring.
# Mirrors the frontend's DISPOSABLE_EMAIL_DOMAINS
# (src/lib/disposableEmailDomains.js) — keep both in sync.
DISPOSABLE_EMAIL_DOMAINS = frozenset({
    "mailinator.com", "mailinator.net", "mailinator.org",
    "guerrillamail.com", "guerrillamail.info", "guerrillamail.biz",
    "guerrillamail.de", "guerrillamail.net", "guerrillamail.org",
    "sharklasers.com", "grr.la", "guerrillamailblock.com",
    "10minutemail.com", "10minutemail.net", "10minutemail.co.uk",
    "temp-mail.org", "tempmail.com", "tempmail.net", "tempmailo.com",
    "throwawaymail.com", "yopmail.com", "yopmail.fr", "yopmail.net",
    "trashmail.com", "trashmail.net", "trashmail.me",
    "getnada.com", "dispostable.com", "fakeinbox.com",
    "maildrop.cc", "mintemail.com", "mailnesia.com", "mailcatch.com",
    "moakt.com", "spamgourmet.com", "spam4.me", "mytemp.email",
    "emailondeck.com", "tempinbox.com", "discard.email", "discardmail.com",
    "mohmal.com", "tempr.email", "temporarymail.com",
    "burnermail.io", "luxusmail.org", "mytrashmail.com", "jetable.org",
    "mailexpire.com", "incognitomail.org",
})

DISPOSABLE_EMAIL_MESSAGE = "Please use a permanent email address — disposable/temporary email providers aren't accepted."


def validate_not_disposable_email(email: str) -> str:
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        raise ValueError(DISPOSABLE_EMAIL_MESSAGE)
    return email


DELIVERABILITY_ERROR_MESSAGE = "Please enter a valid email address that you can access."


def validate_reachable_email(email: str) -> str:
    """A live DNS lookup confirming the domain actually has mail servers (MX, or an
    A/AAAA fallback) — catches typo'd or made-up domains synchronously, before any
    account or verification email is created. This is on top of, not instead of,
    the verification link: DNS can only confirm the *domain* can receive mail, not
    that this specific mailbox exists or belongs to the person registering —
    that's what clicking the link proves."""
    try:
        check_email_deliverable(email, check_deliverability=True, timeout=5)
    except EmailNotValidError:
        raise ValueError(DELIVERABILITY_ERROR_MESSAGE)
    except Exception:
        # A DNS/network hiccup on our end isn't a verdict about the address —
        # don't block every signup in the app over an infrastructure blip.
        pass
    return email


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: EmailStr) -> EmailStr:
        email = str(value)
        validate_not_disposable_email(email)
        validate_reachable_email(email)
        return value

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