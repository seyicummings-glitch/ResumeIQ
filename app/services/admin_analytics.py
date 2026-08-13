"""Pure aggregation helpers for the admin analytics endpoint.

Kept separate from app/routes/admin.py (and free of any DB session) so the
aggregation logic itself can be unit tested without a database.
"""
from collections import Counter


def compute_top_missing_skills(result_jsons, top_n=10):
    """Flatten `skill_match.missing_skills` out of a batch of AnalysisResult
    `result_json` payloads and return the most frequently missing skills.

    Args:
        result_jsons: iterable of dicts (or None/falsy entries, which are
            skipped) shaped like the match_result payload produced by
            matching_engine.calculate_overall_match, i.e. each containing
            result["skill_match"]["missing_skills"] as a list of strings.
        top_n: maximum number of entries to return.

    Returns:
        list of {"skill": str, "count": int}, sorted by count desc, then
        skill name asc as a tiebreaker for stable output.
    """
    counter = Counter()
    for result in result_jsons or []:
        if not result:
            continue
        skill_match = result.get("skill_match") or {}
        missing_skills = skill_match.get("missing_skills") or []
        for skill in missing_skills:
            if skill:
                counter[skill] += 1

    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [{"skill": skill, "count": count} for skill, count in ranked[:top_n]]
