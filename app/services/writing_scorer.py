"""
Rule-based writing-quality scorer for resume experience bullets.

Answers a different question again from ats_scorer.py and matching_engine.py:
not "would an ATS parse this" or "does this match the job" but "is this
well-written, results-oriented resume copy?" Scored the same way as the
other scorers here: deterministic, bucketed checks over already-parsed
text, no ML/AI involved. Final score is a weighted sum out of 100:

    overall_writing_score = action_verb_score (30)
                           + quantification_score (30)
                           + conciseness_score (20)
                           + weak_language_score (20)
"""
import re

STRONG_VERBS = {
    "led", "built", "designed", "developed", "created", "launched", "architected",
    "implemented", "delivered", "improved", "reduced", "increased", "optimized",
    "automated", "migrated", "scaled", "drove", "spearheaded", "mentored",
    "managed", "coordinated", "negotiated", "streamlined", "engineered",
    "established", "founded", "shipped", "resolved", "accelerated", "cut",
    "boosted", "grew", "generated", "saved", "achieved", "transformed",
    "authored", "pioneered", "orchestrated", "restructured", "modernized",
}

WEAK_PHRASES = [
    "responsible for", "duties included", "worked on", "helped with",
    "in charge of", "tasked with", "involved in", "assisted with",
]

BULLET_PREFIX_RE = re.compile(r"^\s*[•\-*•]\s*|^\s*\d+[.)]\s*")


def _split_bullets(experience_text: str) -> list:
    """Treat each non-trivial line of the experience section as one bullet/statement."""
    lines = [line.strip() for line in (experience_text or "").split("\n")]
    return [line for line in lines if len(line) > 15]


def score_action_verbs(bullets: list) -> dict:
    """Score how many bullets open with a strong action verb (max 30)."""
    if not bullets:
        return {"action_verb_score": 0, "strong_verb_ratio": 0, "issues": ["No experience bullets found to evaluate."]}

    strong_count = 0
    for bullet in bullets:
        clean = BULLET_PREFIX_RE.sub("", bullet).strip()
        first_word = re.match(r"[A-Za-z]+", clean)
        if first_word and first_word.group(0).lower() in STRONG_VERBS:
            strong_count += 1

    ratio = strong_count / len(bullets)
    score = round(ratio * 30)
    issues = []
    if ratio < 0.5:
        issues.append("Fewer than half of your bullets open with a strong action verb (e.g. Led, Built, Improved).")

    return {"action_verb_score": score, "strong_verb_ratio": round(ratio, 2), "issues": issues}


def score_quantification(bullets: list) -> dict:
    """Score how many bullets include a number or metric (max 30)."""
    if not bullets:
        return {"quantification_score": 0, "quantified_ratio": 0, "issues": []}

    number_re = re.compile(r"\d")
    quantified_count = sum(1 for bullet in bullets if number_re.search(bullet))
    ratio = quantified_count / len(bullets)
    score = round(ratio * 30)
    issues = []
    if ratio < 0.3:
        issues.append("Few bullets include a number, percentage, or metric — quantified results are more persuasive to reviewers.")

    return {"quantification_score": score, "quantified_ratio": round(ratio, 2), "issues": issues}


def score_conciseness(bullets: list) -> dict:
    """Score bullet length — too short lacks detail, too long is hard to scan (max 20)."""
    if not bullets:
        return {"conciseness_score": 0, "avg_words_per_bullet": 0, "issues": []}

    word_counts = [len(bullet.split()) for bullet in bullets]
    avg_words = sum(word_counts) / len(word_counts)
    issues = []

    if avg_words < 6:
        score = 8
        issues.append("Bullets are very short on average — add more detail on scope and impact.")
    elif avg_words > 35:
        score = 10
        issues.append("Bullets are quite long on average — tighten each to one clear achievement.")
    else:
        score = 20

    return {"conciseness_score": score, "avg_words_per_bullet": round(avg_words, 1), "issues": issues}


def score_weak_language(bullets: list) -> dict:
    """Penalize passive, low-impact phrasing (max 20)."""
    if not bullets:
        return {"weak_language_score": 0, "issues": []}

    flagged = sum(1 for bullet in bullets if any(phrase in bullet.lower() for phrase in WEAK_PHRASES))
    ratio = flagged / len(bullets)
    score = round(20 * (1 - ratio))
    issues = []
    if flagged > 0:
        issues.append(
            f'{flagged} bullet(s) use passive phrasing like "responsible for" or "worked on" — '
            "lead with what you did and its result instead."
        )

    return {"weak_language_score": score, "issues": issues}


def calculate_writing_score(structured_data: dict) -> dict:
    """Combine all sub-scores into a weighted 0-100 writing-quality score."""
    bullets = _split_bullets(structured_data.get("experience", ""))

    action_verbs = score_action_verbs(bullets)
    quantification = score_quantification(bullets)
    conciseness = score_conciseness(bullets)
    weak_language = score_weak_language(bullets)

    overall = (
        action_verbs["action_verb_score"]
        + quantification["quantification_score"]
        + conciseness["conciseness_score"]
        + weak_language["weak_language_score"]
    )

    all_issues = (
        action_verbs["issues"]
        + quantification["issues"]
        + conciseness["issues"]
        + weak_language["issues"]
    )

    return {
        "overall_writing_score": overall,
        "bullet_count": len(bullets),
        "action_verbs": action_verbs,
        "quantification": quantification,
        "conciseness": conciseness,
        "weak_language": weak_language,
        "issues": all_issues,
    }
