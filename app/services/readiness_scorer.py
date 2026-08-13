"""
Composite "hiring readiness" score — a single number combining how well a
resume would survive ATS screening, how well it matches this specific job,
how many required skills are covered, and how well-written it is.

Not a new signal of its own: purely a weighted blend of scores already
computed by ats_scorer, matching_engine, and writing_scorer, so it moves
predictably with the sub-scores it's built from.

    hiring_readiness_score = ats_score * 0.25
                            + match_score * 0.35
                            + skill_score * 0.20
                            + writing_score * 0.20
"""

WEIGHTS = {
    "ats": 0.25,
    "match": 0.35,
    "skill": 0.20,
    "writing": 0.20,
}


def calculate_hiring_readiness(ats_score: float, match_score: float, skill_score: float, writing_score: float) -> float:
    readiness = (
        ats_score * WEIGHTS["ats"]
        + match_score * WEIGHTS["match"]
        + skill_score * WEIGHTS["skill"]
        + writing_score * WEIGHTS["writing"]
    )
    return round(readiness, 2)


def explain_hiring_readiness(readiness_score: float, ats_score: float, match_score: float, skill_score: float, writing_score: float) -> str:
    """Plain-language breakdown of the composite score above, naming whichever
    sub-score is dragging it down the most so it's clear where to focus."""
    components = [
        ("ATS parseability", ats_score, WEIGHTS["ats"]),
        ("job description match", match_score, WEIGHTS["match"]),
        ("skill match", skill_score, WEIGHTS["skill"]),
        ("writing quality", writing_score, WEIGHTS["writing"]),
    ]
    lowest_label, lowest_score, _ = min(components, key=lambda c: c[1])

    lead = (
        f"Hiring readiness is {readiness_score}%, a weighted blend of ATS parseability (25%), job description "
        f"match (35%), skill match (20%), and writing quality (20%)."
    )
    if all(score >= 80 for _, score, _ in components):
        return f"{lead} All of these are already strong."
    return f"{lead} The lowest-scoring factor right now is {lowest_label} ({lowest_score}%) — improving that would raise this score the most."
