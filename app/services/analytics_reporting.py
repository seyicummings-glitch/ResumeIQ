"""Aggregation/reporting over AnalyticsEvent for the Admin Dashboard — the
read side of app/services/analytics.py's track_event(). Two aggregation
styles are used deliberately:

  - Plain counts/group-bys on non-JSON columns (event_type, feature_name,
    created_at) stay as SQL queries — portable across the SQLite used in
    tests and the real Postgres database.
  - Anything that needs to look inside `metadata` (top viewed skills, top
    opened courses, ...) is aggregated in Python after fetching the matching
    rows, rather than using a JSON path operator in SQL. Postgres and SQLite
    have different JSON extraction syntax, and this codebase's test suite
    runs against in-memory SQLite while production is Postgres — Python-side
    aggregation (via collections.Counter, mirroring the existing
    admin_analytics.compute_top_missing_skills pattern) sidesteps that
    entirely and is plenty fast at this data volume.
"""
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analytics_models import AnalyticsEvent
from app.models.models import User


def count_events(db: Session, event_type: str, since: datetime | None = None) -> int:
    query = db.query(func.count(AnalyticsEvent.id)).filter(AnalyticsEvent.event_type == event_type)
    if since is not None:
        query = query.filter(AnalyticsEvent.created_at >= since)
    return query.scalar() or 0


def count_events_any(db: Session, event_types: list[str], since: datetime | None = None) -> int:
    """Count of events matching ANY of the given event_types — e.g. "total
    interviews" might mean interview_started OR voice/text-specific starts,
    depending on how a caller wants to define "total"."""
    query = db.query(func.count(AnalyticsEvent.id)).filter(AnalyticsEvent.event_type.in_(event_types))
    if since is not None:
        query = query.filter(AnalyticsEvent.created_at >= since)
    return query.scalar() or 0


def top_metadata_values(
    db: Session, event_type: str, metadata_key: str, top_n: int = 10, since: datetime | None = None
) -> list[dict]:
    """Top-N most common values of metadata[metadata_key] across events of
    this type — e.g. the most-viewed skill names, most-opened course/video
    titles. Returns [{"value": str, "count": int}, ...] sorted by count desc."""
    query = db.query(AnalyticsEvent.event_metadata).filter(AnalyticsEvent.event_type == event_type)
    if since is not None:
        query = query.filter(AnalyticsEvent.created_at >= since)

    values = []
    for (metadata,) in query.all():
        value = (metadata or {}).get(metadata_key)
        if value:
            values.append(value)

    return [{"value": value, "count": count} for value, count in Counter(values).most_common(top_n)]


def most_used_features(db: Session, since: datetime | None = None, top_n: int = 10) -> list[dict]:
    query = db.query(AnalyticsEvent.feature_name, func.count(AnalyticsEvent.id))
    if since is not None:
        query = query.filter(AnalyticsEvent.created_at >= since)
    rows = query.group_by(AnalyticsEvent.feature_name).order_by(func.count(AnalyticsEvent.id).desc()).limit(top_n).all()
    return [{"feature": feature, "count": count} for feature, count in rows]


# ---------------------------------------------------------------------------
# Time-series helpers — bucketed in Python (see module docstring for why),
# and generic over "a list of timestamps" so the same bucketing logic works
# whether the timestamps come from AnalyticsEvent.created_at or any other
# table's own date column (e.g. User.created_at for user growth).
# ---------------------------------------------------------------------------

def _bucket_key(dt: datetime, granularity: str) -> str:
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    if granularity == "week":
        week_start = dt - timedelta(days=dt.weekday())  # Monday
        return week_start.strftime("%Y-%m-%d")
    if granularity == "month":
        return dt.strftime("%Y-%m")
    raise ValueError(f"Unknown granularity: {granularity!r} (expected 'day', 'week', or 'month')")


def series_from_timestamps(timestamps: list[datetime], granularity: str = "day") -> list[dict]:
    counts = Counter(_bucket_key(ts, granularity) for ts in timestamps if ts is not None)
    return [{"date": key, "count": count} for key, count in sorted(counts.items())]


def event_series(db: Session, event_type: str, since: datetime, granularity: str = "day") -> list[dict]:
    rows = (
        db.query(AnalyticsEvent.created_at)
        .filter(AnalyticsEvent.event_type == event_type, AnalyticsEvent.created_at >= since)
        .all()
    )
    return series_from_timestamps([row[0] for row in rows], granularity)


def column_series(db: Session, date_column, since: datetime, granularity: str = "day") -> list[dict]:
    """Same as event_series but for any other table's own date column (e.g.
    User.created_at) — used where a direct table count is more complete than
    an event count would be (see admin_dashboard.py for which is used where)."""
    rows = db.query(date_column).filter(date_column >= since).all()
    return series_from_timestamps([row[0] for row in rows], granularity)


def merge_series(named_series: dict[str, list[dict]]) -> list[dict]:
    """Merges several {"date", "count"} series that may not share the same
    set of dates into one multi-series-chart-friendly list, e.g.
    {"uploads": [...], "analyses": [...]} -> [{"date": d, "uploads": n, "analyses": m}, ...]
    with 0 filled in for any bucket a given series had no events in."""
    all_dates = sorted({row["date"] for series in named_series.values() for row in series})
    lookups = {name: {row["date"]: row["count"] for row in series} for name, series in named_series.items()}
    return [
        {"date": date, **{name: lookups[name].get(date, 0) for name in named_series}}
        for date in all_dates
    ]


# ---------------------------------------------------------------------------
# Activity feed
# ---------------------------------------------------------------------------

_ACTIVITY_TEMPLATES = {
    "user_registered": "{name} joined ResumeIQ",
    "user_login": "{name} logged in",
    "profile_updated": "{name} updated their profile",
    "resume_uploaded": "{name} uploaded a resume",
    "resume_analyzed": "{name} analyzed a resume",
    "ats_score_generated": "{name} generated an ATS score",
    "resume_reanalyzed": "{name} re-analyzed a resume",
    "resume_downloaded": "{name} downloaded a resume",
    "ai_resume_created": "{name} created a new AI resume",
    "ai_resume_saved": "{name} saved an AI-built resume",
    "ai_resume_regenerated": "{name} regenerated an AI resume",
    "ai_resume_downloaded": "{name} downloaded an AI-built resume",
    "ai_resume_suggestion_generated": "{name} generated AI resume suggestions",
    "ai_builder_started": "{name} started building a resume with AI",
    "ai_builder_completed": "{name} finished an AI resume build",
    "assessment_started": "{name} started a skill assessment",
    "assessment_completed": "{name} completed a skill assessment",
    "interview_started": "{name} started a mock interview",
    "interview_completed": "{name} completed an interview",
    "voice_interview_started": "{name} started a voice interview",
    "text_interview_started": "{name} started a text interview",
    "interview_feedback_generated": "{name} received interview feedback",
    "roadmap_generated": "{name} generated a roadmap",
    "roadmap_completed": "{name} completed a learning roadmap",
    "skill_viewed": "{name} viewed a roadmap skill",
    "course_opened": "{name} opened a recommended course",
    "youtube_resource_opened": "{name} opened a video tutorial",
    "documentation_opened": "{name} opened a documentation link",
    "document_generated": "{name} generated a document",
    "document_downloaded": "{name} downloaded a document",
}


def _describe_event(event_type: str, name: str) -> str:
    template = _ACTIVITY_TEMPLATES.get(event_type)
    if template:
        return template.format(name=name)
    return f"{name} performed {event_type.replace('_', ' ')}"


def get_activity_feed(db: Session, limit: int = 20) -> list[dict]:
    """Most recent platform activity, newest first — every row from
    AnalyticsEvent joined to the acting user's display name."""
    rows = (
        db.query(AnalyticsEvent, User)
        .outerjoin(User, User.id == AnalyticsEvent.user_id)
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    feed = []
    for event, user in rows:
        name = (user.full_name or user.email) if user else "Someone"
        feed.append({
            "id": event.id,
            "eventType": event.event_type,
            "featureName": event.feature_name,
            "text": _describe_event(event.event_type, name),
            "timestamp": event.created_at,
        })
    return feed
