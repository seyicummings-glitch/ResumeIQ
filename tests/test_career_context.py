from types import SimpleNamespace
from app.services.career_context import find_roadmap_topic, topic_context_text


def _roadmap(stages):
    return SimpleNamespace(stages_json=stages)


def test_find_roadmap_topic_locates_by_key():
    roadmap = _roadmap([
        {"stage": "Foundation", "topics": [{"topic_key": "0-0", "title": "Git"}, {"topic_key": "0-1", "title": "Testing"}]},
        {"stage": "Intermediate", "topics": [{"topic_key": "1-0", "title": "Docker"}]},
    ])
    topic = find_roadmap_topic(roadmap, "1-0")
    assert topic["title"] == "Docker"


def test_find_roadmap_topic_returns_none_when_not_found_or_missing_inputs():
    roadmap = _roadmap([{"stage": "Foundation", "topics": [{"topic_key": "0-0", "title": "Git"}]}])
    assert find_roadmap_topic(roadmap, "9-9") is None
    assert find_roadmap_topic(roadmap, None) is None
    assert find_roadmap_topic(None, "0-0") is None


def test_topic_context_text_includes_key_fields():
    topic = {
        "title": "Distributed locking with Redis",
        "why_it_matters": "Prevents race conditions.",
        "current_gap": "Not yet demonstrated.",
        "learning_objectives": ["Implement a lock", "Handle expiration"],
    }
    text = topic_context_text(topic)
    assert "Distributed locking with Redis" in text
    assert "Prevents race conditions." in text
    assert "Not yet demonstrated." in text
    assert "Implement a lock" in text
    assert "Handle expiration" in text
