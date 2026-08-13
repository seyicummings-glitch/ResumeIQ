from app.models.analytics_models import AnalyticsEvent
from app.services.analytics import (
    parse_user_agent,
    extract_client_ip,
    track_event,
    EVENT_TYPES,
    FEATURE_RESUME_ANALYZER,
)


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    def __init__(self, headers=None, client_host="203.0.113.5"):
        self.headers = headers or {}
        self.client = _FakeClient(client_host)


def test_parse_user_agent_detects_chrome_windows_desktop():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    result = parse_user_agent(ua)
    assert result == {"browser": "Chrome", "operating_system": "Windows", "device_type": "desktop"}


def test_parse_user_agent_detects_safari_iphone_mobile():
    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"
    result = parse_user_agent(ua)
    assert result["browser"] == "Safari"
    assert result["operating_system"] == "iOS"
    assert result["device_type"] == "mobile"


def test_parse_user_agent_detects_edge():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36 Edg/120.0"
    assert parse_user_agent(ua)["browser"] == "Edge"


def test_parse_user_agent_detects_firefox_linux():
    ua = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
    result = parse_user_agent(ua)
    assert result["browser"] == "Firefox"
    assert result["operating_system"] == "Linux"


def test_parse_user_agent_detects_ipad_tablet():
    ua = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"
    assert parse_user_agent(ua)["device_type"] == "tablet"


def test_parse_user_agent_handles_missing_ua():
    assert parse_user_agent(None) == {"browser": "Unknown", "operating_system": "Unknown", "device_type": "unknown"}
    assert parse_user_agent("") == {"browser": "Unknown", "operating_system": "Unknown", "device_type": "unknown"}


def test_extract_client_ip_prefers_x_forwarded_for():
    request = _FakeRequest(headers={"x-forwarded-for": "198.51.100.1, 10.0.0.1"}, client_host="10.0.0.1")
    assert extract_client_ip(request) == "198.51.100.1"


def test_extract_client_ip_falls_back_to_client_host():
    request = _FakeRequest(client_host="203.0.113.5")
    assert extract_client_ip(request) == "203.0.113.5"


def test_extract_client_ip_handles_no_request():
    assert extract_client_ip(None) is None


def test_track_event_writes_row_with_ua_and_ip_parsed(db_session):
    request = _FakeRequest(
        headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36", "x-forwarded-for": "198.51.100.9"},
        client_host="10.0.0.1",
    )
    event = track_event(
        db_session, EVENT_TYPES["RESUME_UPLOADED"], FEATURE_RESUME_ANALYZER,
        user_id=42, metadata={"resume_id": 7}, request=request, session_id="sess-123",
    )
    assert event is not None
    assert event.id is not None

    row = db_session.query(AnalyticsEvent).first()
    assert row.event_type == "resume_uploaded"
    assert row.feature_name == "resume_analyzer"
    assert row.user_id == 42
    assert row.event_metadata == {"resume_id": 7}
    assert row.browser == "Chrome"
    assert row.device_type == "desktop"
    assert row.operating_system == "Windows"
    assert row.ip_address == "198.51.100.9"
    assert row.session_id == "sess-123"


def test_track_event_works_with_no_request_at_all(db_session):
    event = track_event(db_session, EVENT_TYPES["USER_LOGIN"], "authentication", user_id=1)
    assert event is not None
    assert event.browser == "Unknown"
    assert event.ip_address is None
    assert event.session_id is None


def test_track_event_never_raises_when_db_session_is_broken():
    class _BrokenSession:
        def add(self, _obj):
            raise RuntimeError("connection lost")

    # Must not raise -- a tracking failure can never break the real user action it's attached to.
    result = track_event(_BrokenSession(), EVENT_TYPES["USER_LOGIN"], "authentication", user_id=1)
    assert result is None


def test_event_types_registry_has_no_duplicate_values():
    values = list(EVENT_TYPES.values())
    assert len(values) == len(set(values))
