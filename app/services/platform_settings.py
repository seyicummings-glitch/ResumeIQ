"""
Central helpers for reading admin-configurable AppSetting values (Admin
Settings page), with sensible defaults so the app behaves the same as before
these settings existed if no settings row has been created yet.
"""
from sqlalchemy.orm import Session
from app.models.admin_models import AppSetting

DEFAULT_MAX_UPLOAD_MB = 10
DEFAULT_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}
DEFAULT_RATE_LIMIT_PER_MINUTE = 60


def get_settings(db: Session) -> AppSetting | None:
    return db.query(AppSetting).first()


def is_ai_enabled(db: Session) -> bool:
    setting = get_settings(db)
    return setting.ai_suggestions_enabled if setting else True


def get_upload_limits(db: Session) -> tuple[set[str], int]:
    """Returns (allowed_extensions, max_size_mb)."""
    setting = get_settings(db)
    if not setting:
        return DEFAULT_ALLOWED_EXTENSIONS, DEFAULT_MAX_UPLOAD_MB

    allowed = set(setting.allowed_file_types.split(",")) if setting.allowed_file_types else DEFAULT_ALLOWED_EXTENSIONS
    return allowed, setting.max_upload_size_mb
