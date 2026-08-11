"""Resolves real, clickable learning-resource links for a roadmap topic's
skill/title — admin-curated where one exists (app/models/skill_resource_models.py),
generated search links otherwise, so a topic never shows up with nowhere to
click through to. Used by app/routes/roadmap.py at serialization time, which
means it applies uniformly to both the AI-generated and rule-based roadmap
paths without either needing to know about it.
"""
import re
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from app.models.skill_resource_models import SkillResource


def normalize_skill_key(skill: str) -> str:
    """Lowercases and strips to bare alphanumerics/spaces so minor formatting
    differences ("Node.js" vs "node js") still match the same curated row."""
    return re.sub(r"[^a-z0-9 ]", "", (skill or "").lower()).strip()


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


def _generated_links(skill: str) -> dict:
    query = quote_plus(skill)
    return {
        "youtubeUrl": f"https://www.youtube.com/results?search_query={query}+tutorial",
        "courseUrl": f"https://www.google.com/search?q={query}+online+course",
        "docsUrl": f"https://www.google.com/search?q={query}+official+documentation",
        "curated": False,
    }


def get_resource_links(skill: str, all_resources: list[SkillResource]) -> dict:
    """`all_resources` is the full SkillResource table, fetched once by the
    caller (see app/routes/roadmap.py) rather than re-queried per topic —
    a roadmap has 15-20 topics, and this table is small enough to hold in
    memory for the duration of one request."""
    normalized = normalize_skill_key(skill)
    match = _find_best_match(normalized, all_resources)

    if match is None:
        return _generated_links(skill)

    return {
        "youtubeUrl": match.youtube_url or None,
        "courseUrl": match.course_url or None,
        "docsUrl": match.docs_url or None,
        "curated": True,
    }


def fetch_all_resources(db: Session) -> list[SkillResource]:
    return db.query(SkillResource).all()
