"""The centralized event-tracking table backing the Admin Dashboard's real,
live analytics — every significant user action across the platform writes
one row here (see app/services/analytics.py's track_event()). Deliberately a
single generic table rather than one table per feature: the set of things
worth tracking grows over time, and a generic (event_type, feature_name,
metadata) shape lets a new event type ship without a schema migration, at
the cost of aggregation queries needing to filter by event_type/feature_name
instead of querying a dedicated table."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)  # event_id
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null for pre-login/anonymous events
    event_type = Column(String, nullable=False, index=True)  # e.g. "resume_uploaded"
    feature_name = Column(String, nullable=False, index=True)  # e.g. "resume_analyzer"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # timestamp
    # Python attribute renamed from the reserved `metadata` (SQLAlchemy's declarative
    # base already owns that name) but the actual DB column is still called "metadata"
    # per the spec.
    event_metadata = Column("metadata", JSON, nullable=True)
    browser = Column(String, nullable=True)
    device_type = Column(String, nullable=True)  # "desktop" | "mobile" | "tablet" | "unknown"
    operating_system = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    session_id = Column(String, nullable=True, index=True)
