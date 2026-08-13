"""Centralized analytics/event tracking service. track_event() is the single
call site every route in the platform uses to record a significant user
action — see EVENT_TYPES below for the full registry of what's tracked.

Deliberately fire-and-forget: track_event() never raises. A real user action
(uploading a resume, saving an analysis, completing an interview) must never
fail because analytics logging hiccupped — the DB write is wrapped and any
failure is logged and swallowed, matching how this codebase treats other
best-effort side channels (e.g. email sending in auth.py).

No FastAPI import here beyond the Request type hint — this stays a plain
service module callable from any route the same way ai_suggestions.py etc.
are, mirroring the codebase's existing separation of routes (HTTP glue) from
services (the actual logic).
"""
import logging
import re

from sqlalchemy.orm import Session

from app.models.analytics_models import AnalyticsEvent

logger = logging.getLogger(__name__)

try:  # pragma: no cover - Request is only used for a type hint, never constructed here
    from starlette.requests import Request
except ImportError:  # pragma: no cover
    Request = None  # type: ignore


# ---------------------------------------------------------------------------
# Event registry — one entry per event_type this platform tracks, grouped by
# feature. Not DB-enforced (event_type is a plain string column, matching the
# rest of this codebase's convention for status/type-like fields), but kept
# here as the single source of truth so route code references a constant
# instead of a hand-typed string that could silently drift/typo.
# ---------------------------------------------------------------------------

FEATURE_AUTH = "authentication"
FEATURE_RESUME_ANALYZER = "resume_analyzer"
FEATURE_AI_BUILDER = "ai_resume_builder"
FEATURE_SKILL_ASSESSMENT = "skill_assessment"
FEATURE_INTERVIEW = "interview_practice"
FEATURE_ROADMAP = "learning_roadmap"
FEATURE_DOCUMENTS = "documents"
FEATURE_SUBSCRIPTION = "subscription"

EVENT_TYPES = {
    # Authentication
    "USER_REGISTERED": "user_registered",
    "USER_LOGIN": "user_login",
    "USER_LOGOUT": "user_logout",
    "PASSWORD_RESET": "password_reset",
    "PROFILE_UPDATED": "profile_updated",
    # Resume Analyzer
    "RESUME_UPLOADED": "resume_uploaded",
    "RESUME_ANALYZED": "resume_analyzed",
    "ATS_SCORE_GENERATED": "ats_score_generated",
    "RESUME_REANALYZED": "resume_reanalyzed",
    "RESUME_DOWNLOADED": "resume_downloaded",
    # AI Resume Builder
    "AI_RESUME_CREATED": "ai_resume_created",
    "AI_RESUME_SAVED": "ai_resume_saved",
    "AI_RESUME_REGENERATED": "ai_resume_regenerated",
    "AI_RESUME_DOWNLOADED": "ai_resume_downloaded",
    "AI_RESUME_SUGGESTION_GENERATED": "ai_resume_suggestion_generated",
    "AI_BUILDER_STARTED": "ai_builder_started",
    "AI_BUILDER_COMPLETED": "ai_builder_completed",
    # Skill Assessment
    "ASSESSMENT_STARTED": "assessment_started",
    "ASSESSMENT_COMPLETED": "assessment_completed",
    "ASSESSMENT_SCORED": "assessment_scored",
    "QUESTION_ANSWERED": "question_answered",
    # Interview Practice
    "INTERVIEW_STARTED": "interview_started",
    "INTERVIEW_COMPLETED": "interview_completed",
    "VOICE_INTERVIEW_STARTED": "voice_interview_started",
    "TEXT_INTERVIEW_STARTED": "text_interview_started",
    "FOLLOWUP_GENERATED": "followup_generated",
    "INTERVIEW_FEEDBACK_GENERATED": "interview_feedback_generated",
    # Learning Roadmap
    "ROADMAP_GENERATED": "roadmap_generated",
    "SKILL_VIEWED": "skill_viewed",
    "COURSE_OPENED": "course_opened",
    "YOUTUBE_RESOURCE_OPENED": "youtube_resource_opened",
    "DOCUMENTATION_OPENED": "documentation_opened",
    "ROADMAP_COMPLETED": "roadmap_completed",
    # Documents
    "DOCUMENT_GENERATED": "document_generated",
    "DOCUMENT_DOWNLOADED": "document_downloaded",
    "DOCUMENT_DELETED": "document_deleted",
    # Subscription — defined for forward-compatibility; nothing in this codebase
    # fires these yet (no Stripe checkout/webhook wave exists), see
    # app/services/admin_dashboard.py's Revenue Analytics section for the
    # honest, currently-empty-but-real query wiring for when that wave lands.
    "SUBSCRIPTION_CREATED": "subscription_created",
    "SUBSCRIPTION_RENEWED": "subscription_renewed",
    "SUBSCRIPTION_CANCELLED": "subscription_cancelled",
    "PAYMENT_SUCCESSFUL": "payment_successful",
    "PAYMENT_FAILED": "payment_failed",
}


# ---------------------------------------------------------------------------
# Lightweight User-Agent parsing — regex heuristics, no external dependency.
# Good enough for analytics-grade browser/OS/device breakdowns; not meant to
# be as exhaustive as a dedicated UA-parsing library.
# ---------------------------------------------------------------------------

_BROWSER_PATTERNS = [
    (re.compile(r"Edg/", re.IGNORECASE), "Edge"),
    (re.compile(r"OPR/|Opera", re.IGNORECASE), "Opera"),
    (re.compile(r"Chrome/", re.IGNORECASE), "Chrome"),
    (re.compile(r"CriOS/", re.IGNORECASE), "Chrome"),
    (re.compile(r"FxiOS/|Firefox/", re.IGNORECASE), "Firefox"),
    (re.compile(r"Safari/", re.IGNORECASE), "Safari"),
]

_OS_PATTERNS = [
    (re.compile(r"Windows", re.IGNORECASE), "Windows"),
    # Checked before the macOS pattern below: iPhone/iPad UAs include "like Mac OS X"
    # for compatibility, so a "Mac OS X" substring check alone would misreport every
    # iPhone/iPad as macOS.
    (re.compile(r"iPhone|iPad|iPod|iOS", re.IGNORECASE), "iOS"),
    (re.compile(r"Mac OS X|Macintosh", re.IGNORECASE), "macOS"),
    (re.compile(r"Android", re.IGNORECASE), "Android"),
    (re.compile(r"Linux", re.IGNORECASE), "Linux"),
]


def parse_user_agent(user_agent: str | None) -> dict:
    """Returns {"browser", "operating_system", "device_type"}, each "Unknown"
    when the UA string is missing or nothing recognizable matches."""
    if not user_agent:
        return {"browser": "Unknown", "operating_system": "Unknown", "device_type": "unknown"}

    browser = next((name for pattern, name in _BROWSER_PATTERNS if pattern.search(user_agent)), "Unknown")
    operating_system = next((name for pattern, name in _OS_PATTERNS if pattern.search(user_agent)), "Unknown")

    if re.search(r"iPad|Tablet", user_agent, re.IGNORECASE):
        device_type = "tablet"
    elif re.search(r"Mobi|Android|iPhone", user_agent, re.IGNORECASE):
        device_type = "mobile"
    else:
        device_type = "desktop"

    return {"browser": browser, "operating_system": operating_system, "device_type": device_type}


def extract_client_ip(request) -> str | None:
    """Prefers X-Forwarded-For (set by a reverse proxy/load balancer in front
    of the real deployment) over the raw ASGI connection's client host, which
    is just the proxy's own address when one is present. Takes the first hop
    in X-Forwarded-For (the original client) since later hops are intermediate
    proxies."""
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def track_event(
    db: Session,
    event_type: str,
    feature_name: str,
    user_id: int | None = None,
    metadata: dict | None = None,
    request=None,
    session_id: str | None = None,
) -> AnalyticsEvent | None:
    """Records one analytics event. Never raises — a tracking failure must
    never break the real user action it's attached to. Returns the created
    row, or None if tracking failed (callers should treat this as fire-and-
    forget and never branch on the return value for real behavior)."""
    try:
        user_agent = request.headers.get("user-agent") if request is not None else None
        parsed_ua = parse_user_agent(user_agent)

        event = AnalyticsEvent(
            user_id=user_id,
            event_type=event_type,
            feature_name=feature_name,
            event_metadata=metadata or {},
            browser=parsed_ua["browser"],
            device_type=parsed_ua["device_type"],
            operating_system=parsed_ua["operating_system"],
            ip_address=extract_client_ip(request),
            session_id=session_id,
        )
        db.add(event)
        db.commit()
        return event
    except Exception:
        logger.warning("analytics.track_event failed for event_type=%s feature=%s", event_type, feature_name, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return None
