from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    target_type = Column(String, nullable=False)
    target_label = Column(String, nullable=False)
    status = Column(String, default="open", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AppSetting(Base):
    """Single-row settings table. Callers should read/create the sole row
    (id=1 in practice) rather than assuming multiple configurations exist."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    maintenance_mode = Column(Boolean, default=False, nullable=False)
    ai_suggestions_enabled = Column(Boolean, default=True, nullable=False)
    max_upload_size_mb = Column(Integer, default=10, nullable=False)
    # Includes image types so this matches resume_parser.py's OCR support by
    # default — narrowing this in the admin UI intentionally disables OCR uploads.
    allowed_file_types = Column(String, default=".pdf,.docx,.txt,.png,.jpg,.jpeg", nullable=False)
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    # AI token economy — see app/services/feature_gate.py. Tokens granted to a brand new account
    # at signup, and how often (in hours) a free-plan user's balance is topped back up by that
    # same amount once it runs out. 24h/48h/7d/30d in the admin UI map to 24/48/168/720 here;
    # stored as raw hours rather than an enum so the choice isn't hardcoded to those four.
    free_signup_credits = Column(Integer, default=100, nullable=False)
    free_credit_refresh_hours = Column(Integer, default=720, nullable=False)
    support_email = Column(String, nullable=True)
