from datetime import datetime, timedelta, timezone

from app.models.models import User
from app.models.analytics_models import AnalyticsEvent
from app.services.analytics_reporting import (
    count_events,
    count_events_any,
    top_metadata_values,
    most_used_features,
    series_from_timestamps,
    event_series,
    column_series,
    merge_series,
    get_activity_feed,
)

NOW = datetime.now(timezone.utc)


def _event(db_session, event_type, feature_name="resume_analyzer", user_id=None, metadata=None, created_at=None):
    event = AnalyticsEvent(
        user_id=user_id, event_type=event_type, feature_name=feature_name,
        event_metadata=metadata or {}, created_at=created_at or NOW,
    )
    db_session.add(event)
    db_session.commit()
    return event


def _user(db_session, email="user@example.com"):
    user = User(email=email, hashed_password="x", full_name="Test User", created_at=NOW)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_count_events_counts_only_matching_type(db_session):
    _event(db_session, "resume_uploaded")
    _event(db_session, "resume_uploaded")
    _event(db_session, "resume_downloaded")

    assert count_events(db_session, "resume_uploaded") == 2
    assert count_events(db_session, "resume_downloaded") == 1
    assert count_events(db_session, "nonexistent_event") == 0


def test_count_events_respects_since(db_session):
    _event(db_session, "resume_uploaded", created_at=NOW - timedelta(days=40))
    _event(db_session, "resume_uploaded", created_at=NOW)

    assert count_events(db_session, "resume_uploaded", since=NOW - timedelta(days=1)) == 1


def test_count_events_any_matches_multiple_types(db_session):
    _event(db_session, "voice_interview_started")
    _event(db_session, "text_interview_started")
    _event(db_session, "interview_completed")

    assert count_events_any(db_session, ["voice_interview_started", "text_interview_started"]) == 2


def test_top_metadata_values_ranks_by_frequency(db_session):
    _event(db_session, "skill_viewed", metadata={"skill": "React"})
    _event(db_session, "skill_viewed", metadata={"skill": "React"})
    _event(db_session, "skill_viewed", metadata={"skill": "Docker"})

    result = top_metadata_values(db_session, "skill_viewed", "skill", top_n=10)
    assert result[0] == {"value": "React", "count": 2}
    assert {"value": "Docker", "count": 1} in result


def test_top_metadata_values_ignores_missing_key(db_session):
    _event(db_session, "skill_viewed", metadata={})
    _event(db_session, "skill_viewed", metadata={"skill": "React"})

    result = top_metadata_values(db_session, "skill_viewed", "skill", top_n=10)
    assert result == [{"value": "React", "count": 1}]


def test_most_used_features_ranks_by_frequency(db_session):
    _event(db_session, "resume_uploaded", feature_name="resume_analyzer")
    _event(db_session, "resume_analyzed", feature_name="resume_analyzer")
    _event(db_session, "roadmap_generated", feature_name="learning_roadmap")

    result = most_used_features(db_session)
    assert result[0] == {"feature": "resume_analyzer", "count": 2}
    assert {"feature": "learning_roadmap", "count": 1} in result


def test_series_from_timestamps_buckets_by_day():
    timestamps = [
        datetime(2026, 8, 1, 10, tzinfo=timezone.utc),
        datetime(2026, 8, 1, 22, tzinfo=timezone.utc),
        datetime(2026, 8, 2, 5, tzinfo=timezone.utc),
    ]
    result = series_from_timestamps(timestamps, "day")
    assert result == [{"date": "2026-08-01", "count": 2}, {"date": "2026-08-02", "count": 1}]


def test_series_from_timestamps_buckets_by_month():
    timestamps = [datetime(2026, 8, 1, tzinfo=timezone.utc), datetime(2026, 8, 28, tzinfo=timezone.utc), datetime(2026, 9, 1, tzinfo=timezone.utc)]
    result = series_from_timestamps(timestamps, "month")
    assert result == [{"date": "2026-08", "count": 2}, {"date": "2026-09", "count": 1}]


def test_event_series_filters_by_since(db_session):
    _event(db_session, "resume_uploaded", created_at=NOW - timedelta(days=40))
    _event(db_session, "resume_uploaded", created_at=NOW)

    result = event_series(db_session, "resume_uploaded", since=NOW - timedelta(days=1))
    assert len(result) == 1


def test_column_series_works_on_any_table_date_column(db_session):
    _user(db_session, "a@example.com")
    _user(db_session, "b@example.com")

    result = column_series(db_session, User.created_at, since=NOW - timedelta(days=1))
    assert result == [{"date": NOW.strftime("%Y-%m-%d"), "count": 2}]


def test_merge_series_fills_zero_for_missing_buckets():
    merged = merge_series({
        "uploads": [{"date": "2026-08-01", "count": 3}],
        "downloads": [{"date": "2026-08-02", "count": 1}],
    })
    assert merged == [
        {"date": "2026-08-01", "uploads": 3, "downloads": 0},
        {"date": "2026-08-02", "uploads": 0, "downloads": 1},
    ]


def test_get_activity_feed_orders_newest_first_and_formats_text(db_session):
    user = _user(db_session, "jordan@example.com")
    _event(db_session, "resume_uploaded", user_id=user.id, created_at=NOW - timedelta(minutes=5))
    _event(db_session, "roadmap_generated", user_id=user.id, created_at=NOW)

    feed = get_activity_feed(db_session, limit=10)
    assert len(feed) == 2
    assert feed[0]["eventType"] == "roadmap_generated"
    assert "Test User" in feed[0]["text"] or "jordan@example.com" in feed[0]["text"]
    assert feed[1]["eventType"] == "resume_uploaded"


def test_get_activity_feed_handles_unknown_event_type_gracefully(db_session):
    user = _user(db_session)
    _event(db_session, "some_future_event_type", user_id=user.id)

    feed = get_activity_feed(db_session, limit=10)
    assert "some future event type" in feed[0]["text"]


def test_get_activity_feed_respects_limit(db_session):
    user = _user(db_session)
    for _ in range(5):
        _event(db_session, "resume_uploaded", user_id=user.id)

    feed = get_activity_feed(db_session, limit=2)
    assert len(feed) == 2


def test_get_activity_feed_handles_events_with_no_user(db_session):
    _event(db_session, "user_registered", user_id=None)
    feed = get_activity_feed(db_session, limit=10)
    assert "Someone" in feed[0]["text"]
