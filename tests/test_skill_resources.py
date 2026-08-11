from app.models.skill_resource_models import SkillResource
from app.services.skill_resources import normalize_skill_key, get_resource_links, fetch_all_resources


def test_normalize_skill_key_strips_punctuation_and_case():
    assert normalize_skill_key("Node.js") == "nodejs"
    assert normalize_skill_key("  Docker  ") == "docker"


def test_get_resource_links_returns_curated_when_exact_match():
    resources = [SkillResource(skill_key="docker", skill_label="Docker", youtube_url="https://youtube.com/x", course_url="https://course.com/x", docs_url="https://docs.docker.com")]
    links = get_resource_links("Docker", resources)
    assert links == {"youtubeUrl": "https://youtube.com/x", "courseUrl": "https://course.com/x", "docsUrl": "https://docs.docker.com", "curated": True}


def test_get_resource_links_matches_substring_in_topic_title():
    resources = [SkillResource(skill_key="git", skill_label="Git", youtube_url="https://youtube.com/git", course_url=None, docs_url=None)]
    links = get_resource_links("Version control with Git", resources)
    assert links["curated"] is True
    assert links["youtubeUrl"] == "https://youtube.com/git"
    assert links["courseUrl"] is None  # admin left it blank -- respected, not backfilled with a search link
    assert links["docsUrl"] is None


def test_get_resource_links_falls_back_to_generated_search_links(monkeypatch):
    links = get_resource_links("Some Totally Uncurated Skill", [])
    assert links["curated"] is False
    assert links["youtubeUrl"].startswith("https://www.youtube.com/results?search_query=")
    assert "Some+Totally+Uncurated+Skill" in links["youtubeUrl"] or "Some%20Totally%20Uncurated%20Skill" in links["youtubeUrl"]
    assert links["courseUrl"].startswith("https://www.google.com/search?q=")
    assert links["docsUrl"].startswith("https://www.google.com/search?q=")


def test_fetch_all_resources_returns_table_contents(db_session):
    db_session.add(SkillResource(skill_key="python", skill_label="Python"))
    db_session.commit()
    resources = fetch_all_resources(db_session)
    assert len(resources) == 1
    assert resources[0].skill_key == "python"
