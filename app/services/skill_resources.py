"""Resolves real, clickable learning-resource links for a roadmap topic's
skill/title, as rich video/course cards rather than plain text links.
Three-tier lookup, richest first:

  1. Admin-curated SkillResource row (app/models/skill_resource_models.py) —
     whatever the admin filled in, with a thumbnail auto-derived from the
     YouTube URL even if they didn't type a title/channel/duration.
  2. Built-in curated table below — real, verified YouTube videos (checked
     via web search, not guessed — a hallucinated video ID would be worse
     than no video at all) paired with a named course, for skills common
     enough to be worth shipping pre-curated.
  3. Generated search links — no thumbnail/title/channel to show (there's no
     specific video to point at), just a working search query, so a topic
     never ends up with nowhere to click through to.

Used by app/routes/roadmap.py at serialization time, so it applies uniformly
to both the AI-generated and rule-based roadmap paths without either needing
to know about it.
"""
import re
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from app.models.skill_resource_models import SkillResource


def normalize_skill_key(skill: str) -> str:
    """Lowercases and strips to bare alphanumerics/spaces so minor formatting
    differences ("Node.js" vs "node js") still match the same curated row."""
    return re.sub(r"[^a-z0-9 ]", "", (skill or "").lower()).strip()


_YOUTUBE_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtube\.com/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def extract_youtube_video_id(url: str | None) -> str | None:
    """Supports youtube.com/watch?v=, youtu.be/, /embed/, and /shorts/ URL shapes."""
    if not url:
        return None
    match = _YOUTUBE_ID_PATTERN.search(url)
    return match.group(1) if match else None


def youtube_thumbnail_url(video_id: str | None) -> str | None:
    """YouTube's public thumbnail CDN — no API key needed, just the video ID."""
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else None


# ---------------------------------------------------------------------------
# Built-in curated videos — every entry below was verified via live web
# search (real video ID, title, channel) rather than recalled from memory,
# specifically to avoid ever linking a plausible-sounding but nonexistent or
# mismatched video. Deliberately not exhaustive: unmatched skills fall
# through to the generated-search tier instead of a guessed pick.
# ---------------------------------------------------------------------------

_CURATED_VIDEO_TABLE = [
    (re.compile(r"\breact\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=bMknfKXIFA8",
        "youtube_title": "React Course - Beginner's Tutorial for React JavaScript Library [2022]",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "10 Hours",
        "course_title": "React - The Complete Guide (Maximilian Schwarzmüller)",
        "course_url": "https://www.udemy.com/course/react-the-complete-guide-incl-redux/",
        "course_provider": "Udemy",
        "docs_url": "https://react.dev",
    }),
    (re.compile(r"\bgit\b|\bgithub\b|version control", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=mAFoROnOfHs",
        "youtube_title": "Git & GitHub Crash Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "1.5 Hours",
        "course_title": "Git Complete: The Definitive, Step-by-Step Guide",
        "course_url": "https://www.udemy.com/course/git-complete/",
        "course_provider": "Udemy",
        "docs_url": "https://git-scm.com/doc",
    }),
    (re.compile(r"\bdocker\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=3c-iBn73dDE",
        "youtube_title": "Docker Tutorial for Beginners [FULL COURSE in 3 Hours]",
        "youtube_channel": "TechWorld with Nana",
        "youtube_duration": "3 Hours",
        "course_title": "Docker Mastery by Bret Fisher",
        "course_url": "https://www.udemy.com/course/docker-mastery/",
        "course_provider": "Udemy",
        "docs_url": "https://docs.docker.com",
    }),
    (re.compile(r"\bpython\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
        "youtube_title": "Learn Python - Full Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "4.5 Hours",
        "course_title": "100 Days of Code: The Complete Python Pro Bootcamp",
        "course_url": "https://www.udemy.com/course/100-days-of-code/",
        "course_provider": "Udemy",
        "docs_url": "https://docs.python.org",
    }),
    (re.compile(r"\bsql\b|\bpostgres(ql)?\b|\bmysql\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=HXV3zeQKqGY",
        "youtube_title": "SQL Tutorial - Full Database Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "4 Hours",
        "course_title": "The Complete SQL Bootcamp",
        "course_url": "https://www.udemy.com/course/the-complete-sql-bootcamp/",
        "course_provider": "Udemy",
        "docs_url": "https://www.postgresql.org/docs/",
    }),
    (re.compile(r"\bexcel\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=Vl0H-qTclOg",
        "youtube_title": "Microsoft Excel Tutorial for Beginners - Full Course",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "2.5 Hours",
        "course_title": "Excel Skills for Business Specialization",
        "course_url": "https://www.coursera.org/specializations/excel",
        "course_provider": "Coursera",
        "docs_url": "https://support.microsoft.com/excel",
    }),
    (re.compile(r"\bseo\b|search engine optimization", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=kaWZXRts9ls",
        "youtube_title": "SEO Full Course | SEO Tutorial For Beginners | Complete SEO Training",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "SEO for Beginners: A Basic Search Engine Optimization Tutorial",
        "course_url": "https://www.udemy.com/course/seo-training/",
        "course_provider": "Udemy",
        "docs_url": "https://developers.google.com/search/docs",
    }),
    (re.compile(r"\btableau\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=TPMlZxRRaBQ",
        "youtube_title": "Tableau for Data Science and Data Visualization - Crash Course",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "0.5 Hours",
        "course_title": "Tableau 2022 A-Z: Hands-On Tableau Training For Data Science",
        "course_url": "https://www.udemy.com/course/tableau10/",
        "course_provider": "Udemy",
        "docs_url": "https://help.tableau.com",
    }),
]


def _curated_video_match(normalized_title: str) -> dict | None:
    for pattern, entry in _CURATED_VIDEO_TABLE:
        if pattern.search(normalized_title):
            return entry
    return None


def _find_best_match(normalized_title: str, resources: list[SkillResource]) -> SkillResource | None:
    if not normalized_title:
        return None
    for resource in resources:
        if resource.skill_key == normalized_title:
            return resource
    for resource in resources:
        if resource.skill_key and resource.skill_key in normalized_title:
            return resource
    return None


def _with_thumbnail(payload: dict, youtube_url: str | None) -> dict:
    video_id = extract_youtube_video_id(youtube_url)
    return {**payload, "youtubeVideoId": video_id, "youtubeThumbnailUrl": youtube_thumbnail_url(video_id)}


def _generated_links(skill: str) -> dict:
    query = quote_plus(skill)
    return {
        "youtubeUrl": f"https://www.youtube.com/results?search_query={query}+tutorial",
        "youtubeVideoId": None,
        "youtubeThumbnailUrl": None,
        "youtubeTitle": None,
        "youtubeChannel": None,
        "youtubeDuration": None,
        "courseUrl": f"https://www.google.com/search?q={query}+online+course",
        "courseTitle": None,
        "courseProvider": None,
        "docsUrl": f"https://www.google.com/search?q={query}+official+documentation",
        "curated": False,
    }


def get_resource_links(skill: str, all_resources: list[SkillResource]) -> dict:
    """`all_resources` is the full SkillResource table, fetched once by the
    caller (see app/routes/roadmap.py) rather than re-queried per topic —
    a roadmap has 15-20 topics, and this table is small enough to hold in
    memory for the duration of one request."""
    normalized = normalize_skill_key(skill)

    admin_match = _find_best_match(normalized, all_resources)
    if admin_match is not None:
        return _with_thumbnail({
            "youtubeUrl": admin_match.youtube_url or None,
            "youtubeTitle": admin_match.youtube_title or None,
            "youtubeChannel": admin_match.youtube_channel or None,
            "youtubeDuration": admin_match.youtube_duration or None,
            "courseUrl": admin_match.course_url or None,
            "courseTitle": admin_match.course_title or None,
            "courseProvider": admin_match.course_provider or None,
            "docsUrl": admin_match.docs_url or None,
            "curated": True,
        }, admin_match.youtube_url)

    curated = _curated_video_match(normalized)
    if curated is not None:
        return _with_thumbnail({
            "youtubeUrl": curated["youtube_url"],
            "youtubeTitle": curated["youtube_title"],
            "youtubeChannel": curated["youtube_channel"],
            "youtubeDuration": curated["youtube_duration"],
            "courseUrl": curated["course_url"],
            "courseTitle": curated["course_title"],
            "courseProvider": curated["course_provider"],
            "docsUrl": curated["docs_url"],
            "curated": True,
        }, curated["youtube_url"])

    return _generated_links(skill)


def fetch_all_resources(db: Session) -> list[SkillResource]:
    return db.query(SkillResource).all()
