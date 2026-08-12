from app.models.skill_resource_models import SkillResource
from app.services.skill_resources import (
    normalize_skill_key,
    extract_youtube_video_id,
    youtube_thumbnail_url,
    get_resource_links,
    fetch_all_resources,
)


def test_normalize_skill_key_strips_punctuation_and_case():
    assert normalize_skill_key("Node.js") == "nodejs"
    assert normalize_skill_key("  Docker  ") == "docker"


def test_extract_youtube_video_id_handles_common_url_shapes():
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=bMknfKXIFA8") == "bMknfKXIFA8"
    assert extract_youtube_video_id("https://youtu.be/bMknfKXIFA8") == "bMknfKXIFA8"
    assert extract_youtube_video_id("https://www.youtube.com/embed/bMknfKXIFA8") == "bMknfKXIFA8"
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=bMknfKXIFA8&t=30s") == "bMknfKXIFA8"
    assert extract_youtube_video_id(None) is None
    assert extract_youtube_video_id("https://example.com/not-youtube") is None


def test_youtube_thumbnail_url_builds_from_video_id():
    assert youtube_thumbnail_url("bMknfKXIFA8") == "https://img.youtube.com/vi/bMknfKXIFA8/hqdefault.jpg"
    assert youtube_thumbnail_url(None) is None


def test_get_resource_links_admin_curated_takes_priority_and_gets_thumbnail():
    resources = [SkillResource(
        skill_key="docker", skill_label="Docker",
        youtube_url="https://www.youtube.com/watch?v=CUSTOM12345",
        youtube_title="Admin's Chosen Docker Video", youtube_channel="Some Channel", youtube_duration="2 Hours",
        course_url="https://course.com/x", course_title="Admin Course", course_provider="Admin U",
        docs_url="https://docs.docker.com",
    )]
    links = get_resource_links("Docker", resources)
    assert links["curated"] is True
    assert links["youtubeUrl"] == "https://www.youtube.com/watch?v=CUSTOM12345"
    assert links["youtubeTitle"] == "Admin's Chosen Docker Video"
    assert links["youtubeVideoId"] == "CUSTOM12345"
    assert links["youtubeThumbnailUrl"] == "https://img.youtube.com/vi/CUSTOM12345/hqdefault.jpg"
    assert links["courseTitle"] == "Admin Course"


def test_get_resource_links_admin_curated_without_metadata_still_gets_thumbnail():
    # Admin only filled in the URL -- title/channel/duration are None, but the
    # thumbnail is still derived automatically from the URL alone.
    resources = [SkillResource(skill_key="git", skill_label="Git", youtube_url="https://youtu.be/mAFoROnOfHs")]
    links = get_resource_links("Version control with Git", resources)
    assert links["curated"] is True
    assert links["youtubeTitle"] is None
    assert links["youtubeVideoId"] == "mAFoROnOfHs"
    assert links["youtubeThumbnailUrl"] == "https://img.youtube.com/vi/mAFoROnOfHs/hqdefault.jpg"


def test_get_resource_links_falls_back_to_builtin_curated_video_when_no_admin_match():
    links = get_resource_links("React", [])
    assert links["curated"] is True
    assert links["youtubeChannel"] == "freeCodeCamp.org"
    assert links["youtubeTitle"]
    assert links["youtubeVideoId"] == "bMknfKXIFA8"
    assert links["youtubeThumbnailUrl"] == "https://img.youtube.com/vi/bMknfKXIFA8/hqdefault.jpg"
    assert links["courseProvider"] == "Udemy"


def test_get_resource_links_builtin_curated_matches_topic_containing_skill():
    links = get_resource_links("Learn to use SQL for backend development", [])
    assert links["curated"] is True
    assert links["youtubeChannel"] == "freeCodeCamp.org"


def test_get_resource_links_falls_back_to_generated_search_links_when_nothing_matches():
    links = get_resource_links("Some Totally Uncurated Skill", [])
    assert links["curated"] is False
    assert links["youtubeVideoId"] is None
    assert links["youtubeThumbnailUrl"] is None
    assert links["youtubeTitle"] is None
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
