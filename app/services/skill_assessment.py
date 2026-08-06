"""
Pure functions powering the no-AI fallback path of Skill Assessment: matching
a user's resume skills (plus detected skill gaps) to relevant static
multiple-choice question categories, randomly assembling a personalized,
non-repeating question set, and scoring submitted answers.

No FastAPI/SQLAlchemy imports here, mirroring app/services/matching_engine.py —
this module only deals in plain dicts/lists so it's trivially unit-testable
and callers (the route layer) own all DB/JSON I/O. The primary, AI-generated
path lives in app/services/skill_assessment_ai.py instead — this module is
what runs when AI is disabled or unavailable.
"""
import random

# Lowercased skill-name variant -> category key. Extend as new skills/aliases
# come up; anything not found here falls back to the "general_swe" category.
SKILL_ALIASES: dict[str, str] = {
    # React
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "next": "react",
    "nextjs": "react",
    "next.js": "react",
    "redux": "react",
    # JavaScript
    "javascript": "javascript",
    "js": "javascript",
    "es6": "javascript",
    "ecmascript": "javascript",
    # TypeScript
    "typescript": "typescript",
    "ts": "typescript",
    # Python
    "python": "python",
    "python3": "python",
    "django": "python",
    "flask": "python",
    "fastapi": "python",
    "pandas": "python",
    "numpy": "python",
    # Node.js
    "node": "nodejs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "express": "nodejs",
    "express.js": "nodejs",
    "nestjs": "nodejs",
    # SQL & databases
    "sql": "sql",
    "postgresql": "sql",
    "postgres": "sql",
    "mysql": "sql",
    "sqlite": "sql",
    "mssql": "sql",
    "database": "sql",
    "databases": "sql",
    # Docker & containers
    "docker": "docker",
    "kubernetes": "docker",
    "k8s": "docker",
    "containerization": "docker",
    "containers": "docker",
}

DIFFICULTY_WEIGHT = {"beginner": 1, "intermediate": 2, "advanced": 3}

FALLBACK_CATEGORY = "general_swe"

TECHNICAL_COUNT = 11
SOFT_COUNT = 4

MIN_TOTAL_COUNT = 5
MAX_TOTAL_COUNT = 25
# Matches TECHNICAL_COUNT/SOFT_COUNT's ~11:4 ratio at the default total of 15.
_SOFT_RATIO = SOFT_COUNT / (TECHNICAL_COUNT + SOFT_COUNT)


def distribute_fallback_counts(total_count: int) -> tuple[int, int]:
    """Splits a user-chosen total into (technical_count, soft_count) using the
    same ~73/27 ratio as the default 11/4 split, always summing to exactly
    total_count with at least 1 question of each type."""
    total_count = max(MIN_TOTAL_COUNT, min(MAX_TOTAL_COUNT, total_count))
    soft_count = max(1, round(total_count * _SOFT_RATIO))
    technical_count = total_count - soft_count
    return technical_count, soft_count

# Expanded pool so a restarted fallback assessment has real variety to draw
# from instead of always showing the same "few" scenarios.
SOFT_SCENARIOS = [
    {
        "id": 1,
        "category": "Leadership & Ownership",
        "type": "behavioral",
        "scenario": "You are midway through a sprint and discover a critical bug in a module you did not write. The original author is on vacation. How do you handle this situation?",
        "keywords": ["triage", "severity", "reproduce", "test", "communicate", "escalate", "document", "rollback", "owner", "notify"],
    },
    {
        "id": 2,
        "category": "Communication & Conflict",
        "type": "behavioral",
        "scenario": "A senior colleague insists on an architectural approach you believe will create technical debt. How do you navigate this disagreement professionally and constructively?",
        "keywords": ["data", "trade-off", "document", "propose", "alternative", "listen", "compromise", "escalate", "respect", "evidence"],
    },
    {
        "id": 3,
        "category": "Prioritization",
        "type": "scenario",
        "scenario": 'You have three tasks all labeled "urgent" by different stakeholders, but you can only complete two before the deadline. Walk me through your prioritization process.',
        "keywords": ["impact", "stakeholder", "deadline", "risk", "communicate", "negotiate", "criteria", "trade-off", "align", "clarify"],
    },
    {
        "id": 4,
        "category": "Handling Ambiguity",
        "type": "scenario",
        "scenario": "You're asked to build a feature, but the requirements are vague and the product owner is unavailable for two days. What do you do in the meantime?",
        "keywords": ["assumption", "clarify", "document", "prototype", "risk", "scope", "communicate", "reversible", "research", "async"],
    },
    {
        "id": 5,
        "category": "Failure & Learning",
        "type": "behavioral",
        "scenario": "Describe a time a decision you made caused a production incident or a significant setback. What happened, and what did you change afterward?",
        "keywords": ["root cause", "postmortem", "accountable", "learn", "process", "monitor", "prevent", "communicate", "fix", "impact"],
    },
    {
        "id": 6,
        "category": "Cross-team Collaboration",
        "type": "scenario",
        "scenario": "Another team's changes are blocking your work, and their priorities don't currently include unblocking you. How do you move forward?",
        "keywords": ["align", "stakeholder", "escalate", "workaround", "communicate", "priority", "negotiate", "relationship", "timeline", "unblock"],
    },
    {
        "id": 7,
        "category": "Time Management",
        "type": "scenario",
        "scenario": "You realize two days before a deadline that a feature will take significantly longer than estimated. Walk me through what you do next.",
        "keywords": ["communicate", "scope", "cut", "risk", "estimate", "stakeholder", "negotiate", "transparent", "plan", "trade-off"],
    },
    {
        "id": 8,
        "category": "Feedback",
        "type": "behavioral",
        "scenario": "You receive critical feedback on a pull request that you initially disagree with. How do you respond and resolve it?",
        "keywords": ["listen", "understand", "evidence", "discuss", "compromise", "test", "revise", "respectful", "clarify", "learn"],
    },
]


def match_categories(skills: list[str]) -> list[str]:
    """Lowercase + strip each skill, look up its category via SKILL_ALIASES, return sorted unique matches."""
    matched = set()
    for skill in skills:
        if not skill:
            continue
        key = skill.strip().lower()
        category = SKILL_ALIASES.get(key)
        if category:
            matched.add(category)
    return sorted(matched)


def build_assessment(
    all_questions: list[dict],
    skills: list[str],
    count: int = TECHNICAL_COUNT,
    exclude_ids: list[int] | None = None,
) -> list[dict]:
    """Randomly picks exactly `count` questions (when the bank has that many),
    preferring the categories matched from `skills`, biased toward
    intermediate/advanced difficulty, and avoiding `exclude_ids` (recently
    served questions, e.g. from the user's last attempt) wherever possible so
    restarting produces a genuinely different set rather than the same one."""
    exclude_ids = set(exclude_ids or [])
    categories = match_categories(skills) or [FALLBACK_CATEGORY]

    def pool(category_keys, difficulties, avoid_ids):
        return [
            q
            for q in all_questions
            if q.get("category_key") in category_keys
            and q.get("difficulty") in difficulties
            and q["id"] not in avoid_ids
        ]

    selected: list[dict] = []

    # 1) Matched categories, harder difficulties first, unseen questions only.
    tier1 = pool(categories, ("intermediate", "advanced"), exclude_ids)
    random.shuffle(tier1)
    selected.extend(tier1[:count])

    # 2) Same categories, beginner allowed, still unseen.
    if len(selected) < count:
        chosen_ids = {q["id"] for q in selected}
        tier2 = pool(categories, ("beginner",), exclude_ids | chosen_ids)
        random.shuffle(tier2)
        selected.extend(tier2[: count - len(selected)])

    # 3) Any category, any difficulty, still unseen — guarantees variety even
    #    when only one or two categories matched the resume.
    if len(selected) < count:
        chosen_ids = {q["id"] for q in selected}
        tier3 = [q for q in all_questions if q["id"] not in exclude_ids and q["id"] not in chosen_ids]
        random.shuffle(tier3)
        selected.extend(tier3[: count - len(selected)])

    # 4) Any category/difficulty, ignoring exclude_ids but still never
    #    duplicating a question already picked for *this* set — reuses
    #    recently-served questions rather than shorting the count once the
    #    bank itself can't supply enough fully-unseen ones.
    if len(selected) < count:
        chosen_ids = {q["id"] for q in selected}
        tier4 = [q for q in all_questions if q["id"] not in chosen_ids]
        random.shuffle(tier4)
        selected.extend(tier4[: count - len(selected)])

    # 5) True last resort — the whole bank is smaller than `count`, so the
    #    only way to reach the required count is to repeat a question within
    #    the same set.
    if len(selected) < count and all_questions:
        missing = count - len(selected)
        selected.extend(random.choices(all_questions, k=missing))

    return selected[:count]


def pick_soft_scenarios(count: int = SOFT_COUNT, exclude_ids: list[int] | None = None) -> list[dict]:
    """Randomly picks `count` soft-skill scenarios, avoiding `exclude_ids` (the
    user's most recent attempt) wherever the pool is large enough to allow it."""
    exclude_ids = set(exclude_ids or [])
    pool = [s for s in SOFT_SCENARIOS if s["id"] not in exclude_ids]
    random.shuffle(pool)

    if len(pool) < count:
        chosen_ids = {s["id"] for s in pool}
        leftover = [s for s in SOFT_SCENARIOS if s["id"] not in chosen_ids]
        random.shuffle(leftover)
        pool.extend(leftover)

    return pool[:count]


def score_technical(questions: list[dict], answers: dict[int, int]) -> dict:
    """Weighted technical score (beginner=1, intermediate=2, advanced=3) plus raw correct/total counts."""
    weighted_correct = 0
    max_weight = 0
    correct_count = 0

    for question in questions:
        weight = DIFFICULTY_WEIGHT.get(question.get("difficulty"), 1)
        max_weight += weight
        selected = answers.get(question["id"])
        if selected is not None and selected == question.get("correct_index"):
            weighted_correct += weight
            correct_count += 1

    technical_score = round(weighted_correct / max_weight * 100) if max_weight > 0 else 0

    return {
        "technical_score": technical_score,
        "correct_count": correct_count,
        "total": len(questions),
    }


def score_soft_fallback(scenario: dict, answer_text: str) -> int:
    """Honest, content-aware fallback soft-skill score (used only when AI grading
    is unavailable) — unlike a pure word-count heuristic, this requires the
    answer to actually be on-topic and non-degenerate to score above a few
    points, and is capped well below "excellent" since it's not real grading."""
    text = (answer_text or "").strip()
    words = text.split()
    word_count = len(words)

    if word_count < 15:
        return 0

    unique_ratio = len(set(w.lower() for w in words)) / word_count
    if unique_ratio < 0.3:
        # Degenerate / spammy text (e.g. the same word or phrase repeated) —
        # not a genuine attempt, regardless of length.
        return 5

    text_lower = text.lower()
    keyword_hits = sum(1 for kw in scenario.get("keywords", []) if kw in text_lower)

    base = 30 + min(30, keyword_hits * 8)
    length_bonus = min(15, round(word_count / 12))
    return min(75, base + length_bonus)


def category_breakdown(questions: list[dict], answers: dict[int, int]) -> list[dict]:
    """Per-category correct/total/pct breakdown for the technical questions, sorted by pct descending."""
    stats: dict[str, dict] = {}

    for question in questions:
        category_key = question.get("category_key")
        category_label = question.get("category_label") or question.get("category")
        entry = stats.setdefault(
            category_key,
            {"category_key": category_key, "category_label": category_label, "correct": 0, "total": 0},
        )
        entry["total"] += 1
        selected = answers.get(question["id"])
        if selected is not None and selected == question.get("correct_index"):
            entry["correct"] += 1

    breakdown = []
    for entry in stats.values():
        pct = round(entry["correct"] / entry["total"] * 100) if entry["total"] > 0 else 0
        breakdown.append({**entry, "pct": pct})

    breakdown.sort(key=lambda item: item["pct"], reverse=True)
    return breakdown


def overall_score(technical_score: int, soft_score: int) -> int:
    """Combine technical (70%) and soft-skill (30%) scores into a single overall score."""
    return round(technical_score * 0.7 + soft_score * 0.3)
