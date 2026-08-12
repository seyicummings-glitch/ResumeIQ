from app.models.models import User
from app.models.roadmap_models import LearningRoadmap
from app.models.skill_resource_models import SkillResource
from app.routes.roadmap import _serialize_roadmap


def _user(db_session):
    user = User(email="user@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _roadmap(db_session, user, stages):
    roadmap = LearningRoadmap(user_id=user.id, source="fallback", stages_json=stages)
    db_session.add(roadmap)
    db_session.commit()
    db_session.refresh(roadmap)
    return roadmap


def test_serialize_roadmap_attaches_curated_resource_links(db_session):
    user = _user(db_session)
    db_session.add(SkillResource(
        skill_key="docker", skill_label="Docker",
        youtube_url="https://www.youtube.com/watch?v=3c-iBn73dDE",
        youtube_title="Docker Tutorial for Beginners", youtube_channel="TechWorld with Nana",
        course_url="https://course.com/docker", docs_url="https://docs.docker.com",
    ))
    db_session.commit()

    stages = [{"stage": "Intermediate", "topics": [{"topic_key": "0-0", "title": "Docker", "estimated_hours": 15}]}]
    roadmap = _roadmap(db_session, user, stages)

    result = _serialize_roadmap(db_session, roadmap, user.id)
    links = result["stages"][0]["topics"][0]["resource_links"]
    assert links["curated"] is True
    assert links["youtubeUrl"] == "https://www.youtube.com/watch?v=3c-iBn73dDE"
    assert links["youtubeTitle"] == "Docker Tutorial for Beginners"
    assert links["youtubeVideoId"] == "3c-iBn73dDE"
    assert links["youtubeThumbnailUrl"] == "https://img.youtube.com/vi/3c-iBn73dDE/hqdefault.jpg"
    assert links["courseUrl"] == "https://course.com/docker"
    assert links["docsUrl"] == "https://docs.docker.com"


def test_serialize_roadmap_falls_back_to_generated_links_when_uncurated(db_session):
    user = _user(db_session)
    stages = [{"stage": "Advanced", "topics": [{"topic_key": "0-0", "title": "Some Rare Skill", "estimated_hours": 10}]}]
    roadmap = _roadmap(db_session, user, stages)

    result = _serialize_roadmap(db_session, roadmap, user.id)
    topic = result["stages"][0]["topics"][0]
    assert topic["resource_links"]["curated"] is False
    assert topic["resource_links"]["youtubeUrl"] is not None
