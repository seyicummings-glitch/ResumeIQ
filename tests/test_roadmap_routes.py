import pytest
from fastapi import HTTPException

from app.models.models import User
from app.models.analytics_models import AnalyticsEvent
from app.models.roadmap_models import LearningRoadmap
from app.routes import roadmap as routes


def _user(db_session, target_role="Marketing Manager"):
    user = User(email="user@example.com", hashed_password="x", target_role=target_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _multi_topic_roadmap(db_session, user):
    """Seeded directly rather than via regenerate_roadmap() -- with no analysis and no missing
    skills, build_roadmap()'s honest "no gaps" fallback returns only one topic, which isn't
    useful for a "partial completion" test."""
    stages = [{
        "stage": "Foundation", "description": "d", "estimated_duration": "1 week", "milestone": "m",
        "topics": [
            {"topic_key": "0-0", "title": "Topic A", "estimated_hours": 5},
            {"topic_key": "0-1", "title": "Topic B", "estimated_hours": 5},
        ],
    }]
    roadmap = LearningRoadmap(user_id=user.id, source="fallback", stages_json=stages)
    db_session.add(roadmap)
    db_session.commit()
    db_session.refresh(roadmap)
    return roadmap


def test_regenerate_roadmap_fires_roadmap_generated_event(db_session):
    user = _user(db_session)
    routes.regenerate_roadmap(db=db_session, current_user=user)

    events = db_session.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "roadmap_generated").all()
    assert len(events) == 1
    assert events[0].user_id == user.id
    assert events[0].feature_name == "learning_roadmap"


def test_toggle_all_topics_fires_roadmap_completed_event(db_session):
    user = _user(db_session)
    result = routes.regenerate_roadmap(db=db_session, current_user=user)
    topics = [t for stage in result["roadmap"]["stages"] for t in stage["topics"]]
    assert len(topics) > 0

    for topic in topics:
        routes.toggle_roadmap_topic(routes.RoadmapToggleInput(topic_key=topic["topic_key"]), db=db_session, current_user=user)

    completed_events = db_session.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "roadmap_completed").all()
    assert len(completed_events) == 1


def test_toggle_partial_topics_does_not_fire_roadmap_completed(db_session):
    user = _user(db_session)
    _multi_topic_roadmap(db_session, user)

    routes.toggle_roadmap_topic(routes.RoadmapToggleInput(topic_key="0-0"), db=db_session, current_user=user)

    completed_events = db_session.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "roadmap_completed").all()
    assert len(completed_events) == 0


def test_track_resource_click_video(db_session):
    user = _user(db_session)
    result = routes.track_resource_click(
        routes.ResourceClickInput(resource_type="video", skill_title="React", url="https://youtube.com/watch?v=abc"),
        db=db_session, current_user=user,
    )
    assert result == {"tracked": True}

    event = db_session.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "youtube_resource_opened").first()
    assert event is not None
    assert event.event_metadata == {"skill": "React", "url": "https://youtube.com/watch?v=abc"}


def test_track_resource_click_course_and_docs_and_skill(db_session):
    user = _user(db_session)
    routes.track_resource_click(routes.ResourceClickInput(resource_type="course", skill_title="Docker"), db=db_session, current_user=user)
    routes.track_resource_click(routes.ResourceClickInput(resource_type="docs", skill_title="Docker"), db=db_session, current_user=user)
    routes.track_resource_click(routes.ResourceClickInput(resource_type="skill", skill_title="Docker"), db=db_session, current_user=user)

    event_types = {e.event_type for e in db_session.query(AnalyticsEvent).all()}
    assert {"course_opened", "documentation_opened", "skill_viewed"} <= event_types


def test_track_resource_click_rejects_unknown_resource_type(db_session):
    user = _user(db_session)
    with pytest.raises(HTTPException) as exc_info:
        routes.track_resource_click(routes.ResourceClickInput(resource_type="bogus", skill_title="Docker"), db=db_session, current_user=user)
    assert exc_info.value.status_code == 400
