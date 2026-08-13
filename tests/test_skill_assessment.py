from app.services.skill_assessment import (
    MAX_TOTAL_COUNT,
    MIN_TOTAL_COUNT,
    SOFT_SCENARIOS,
    TECHNICAL_COUNT,
    build_assessment,
    category_breakdown,
    distribute_fallback_counts,
    match_categories,
    overall_score,
    pick_soft_scenarios,
    score_soft_fallback,
    score_technical,
)

SAMPLE_QUESTIONS = [
    {"id": 1, "category_key": "react", "category_label": "React", "difficulty": "beginner", "correct_index": 1},
    {"id": 2, "category_key": "react", "category_label": "React", "difficulty": "intermediate", "correct_index": 1},
    {"id": 3, "category_key": "react", "category_label": "React", "difficulty": "advanced", "correct_index": 1},
    {"id": 4, "category_key": "python", "category_label": "Python", "difficulty": "beginner", "correct_index": 0},
    {"id": 5, "category_key": "python", "category_label": "Python", "difficulty": "intermediate", "correct_index": 1},
    {"id": 6, "category_key": "python", "category_label": "Python", "difficulty": "advanced", "correct_index": 1},
    {"id": 7, "category_key": "general_swe", "category_label": "Software Engineering Fundamentals", "difficulty": "beginner", "correct_index": 1},
]

# A larger synthetic bank so build_assessment tests can actually exercise
# "give me 11" without every test needing to hand-write 11+ questions.
LARGE_BANK = []
for i in range(1, 41):
    category = ["react", "python", "sql", "docker"][i % 4]
    difficulty = ["beginner", "intermediate", "advanced"][i % 3]
    LARGE_BANK.append({
        "id": i,
        "category_key": category,
        "category_label": category.title(),
        "difficulty": difficulty,
        "correct_index": 0,
    })


def test_match_categories_uses_aliases_and_dedupes():
    categories = match_categories(["React", "reactjs", "Python", "unknown-skill", ""])
    assert categories == ["python", "react"]


def test_match_categories_no_match_returns_empty():
    assert match_categories(["cobol", "assembly"]) == []


def test_build_assessment_returns_exactly_the_requested_count():
    questions = build_assessment(LARGE_BANK, ["react", "python"], count=TECHNICAL_COUNT)
    assert len(questions) == TECHNICAL_COUNT
    assert len({q["id"] for q in questions}) == TECHNICAL_COUNT


def test_build_assessment_falls_back_to_general_swe_when_no_skills_match():
    questions = build_assessment(SAMPLE_QUESTIONS, ["cobol"], count=1)
    assert questions
    assert all(q["category_key"] == "general_swe" for q in questions)


def test_build_assessment_guarantees_count_even_with_small_bank():
    # Only 7 questions exist total; asking for 11 must still return 11 by
    # backfilling/reusing rather than silently returning fewer.
    questions = build_assessment(SAMPLE_QUESTIONS, ["react"], count=TECHNICAL_COUNT)
    assert len(questions) == TECHNICAL_COUNT


def test_build_assessment_avoids_recently_served_questions_when_possible():
    first = build_assessment(LARGE_BANK, ["react", "python"], count=TECHNICAL_COUNT)
    second = build_assessment(
        LARGE_BANK, ["react", "python"], count=TECHNICAL_COUNT, exclude_ids=[q["id"] for q in first]
    )
    overlap = {q["id"] for q in first} & {q["id"] for q in second}
    assert overlap == set()


def test_build_assessment_is_randomized_across_calls():
    # With a large bank, two unconstrained draws should very likely differ —
    # this is the fix for "restart shows the exact same questions".
    attempts = [tuple(sorted(q["id"] for q in build_assessment(LARGE_BANK, ["react", "python"], count=TECHNICAL_COUNT))) for _ in range(5)]
    assert len(set(attempts)) > 1


def test_pick_soft_scenarios_returns_requested_count():
    scenarios = pick_soft_scenarios(count=4)
    assert len(scenarios) == 4
    assert len({s["id"] for s in scenarios}) == 4


def test_pick_soft_scenarios_avoids_recently_served_when_pool_allows():
    first = pick_soft_scenarios(count=4)
    second = pick_soft_scenarios(count=4, exclude_ids=[s["id"] for s in first])
    overlap = {s["id"] for s in first} & {s["id"] for s in second}
    assert overlap == set()


def test_pick_soft_scenarios_guarantees_count_even_when_excluding_most_of_pool():
    almost_all_ids = [s["id"] for s in SOFT_SCENARIOS[:-1]]
    scenarios = pick_soft_scenarios(count=4, exclude_ids=almost_all_ids)
    assert len(scenarios) == 4


def test_score_technical_weights_by_difficulty():
    answers = {1: 1, 2: 1, 3: 1, 4: 99, 5: 99, 6: 99, 7: 99}
    result = score_technical(SAMPLE_QUESTIONS, answers)
    assert result["total"] == 7
    assert result["correct_count"] == 3
    assert result["technical_score"] == round(6 / 13 * 100)


def test_score_technical_all_correct_is_100():
    answers = {q["id"]: q["correct_index"] for q in SAMPLE_QUESTIONS}
    result = score_technical(SAMPLE_QUESTIONS, answers)
    assert result["technical_score"] == 100
    assert result["correct_count"] == len(SAMPLE_QUESTIONS)


def test_score_technical_empty_questions_returns_zero():
    result = score_technical([], {})
    assert result["technical_score"] == 0
    assert result["total"] == 0


SCENARIO = SOFT_SCENARIOS[0]

RELEVANT_ANSWER = (
    "I would first triage the severity of the bug, reproduce it locally, write a failing test, "
    "communicate the situation to stakeholders, and document a rollback plan before shipping any fix."
)


def test_score_soft_fallback_blank_answer_scores_zero():
    assert score_soft_fallback(SCENARIO, "") == 0
    assert score_soft_fallback(SCENARIO, "   ") == 0


def test_score_soft_fallback_too_short_scores_zero():
    assert score_soft_fallback(SCENARIO, "I would fix it fast and tell everyone quickly.") == 0


def test_score_soft_fallback_degenerate_repeated_text_scores_near_zero():
    spam = " ".join(["banana"] * 20)
    assert score_soft_fallback(SCENARIO, spam) <= 10


def test_score_soft_fallback_relevant_answer_scores_meaningfully_higher_than_offtopic():
    offtopic = (
        "The weather today is quite pleasant with sunshine and mild temperatures across most of the "
        "region this week according to several independent reports."
    )
    relevant_score = score_soft_fallback(SCENARIO, RELEVANT_ANSWER)
    offtopic_score = score_soft_fallback(SCENARIO, offtopic)
    assert relevant_score > offtopic_score
    assert relevant_score >= 40


def test_score_soft_fallback_is_capped_below_perfect():
    # Even a maximally keyword-stuffed answer should never claim the same
    # confidence as real AI grading.
    stuffed = " ".join(SCENARIO["keywords"] * 5) + " " + RELEVANT_ANSWER
    assert score_soft_fallback(SCENARIO, stuffed) <= 75


def test_category_breakdown_sorted_by_pct_descending():
    answers = {1: 1, 2: 1, 3: 1, 4: 99, 5: 99, 6: 99, 7: 1}
    breakdown = category_breakdown(SAMPLE_QUESTIONS, answers)
    pct_values = [item["pct"] for item in breakdown]
    assert pct_values == sorted(pct_values, reverse=True)
    react_entry = next(item for item in breakdown if item["category_key"] == "react")
    assert react_entry["correct"] == 3
    assert react_entry["total"] == 3
    assert react_entry["pct"] == 100

    python_entry = next(item for item in breakdown if item["category_key"] == "python")
    assert python_entry["correct"] == 0
    assert python_entry["pct"] == 0


def test_overall_score_weights_technical_more_than_soft():
    assert overall_score(technical_score=100, soft_score=0) == 70
    assert overall_score(technical_score=0, soft_score=100) == 30
    assert overall_score(technical_score=80, soft_score=60) == round(80 * 0.7 + 60 * 0.3)


def test_distribute_fallback_counts_default_matches_original_constants():
    technical, soft = distribute_fallback_counts(15)
    assert (technical, soft) == (TECHNICAL_COUNT, 4)


def test_distribute_fallback_counts_always_sums_to_total():
    for total in range(MIN_TOTAL_COUNT, MAX_TOTAL_COUNT + 1):
        technical, soft = distribute_fallback_counts(total)
        assert technical + soft == total, f"failed for total={total}"
        assert technical >= 1 and soft >= 1


def test_distribute_fallback_counts_clamps_out_of_range():
    assert sum(distribute_fallback_counts(1)) == MIN_TOTAL_COUNT
    assert sum(distribute_fallback_counts(1000)) == MAX_TOTAL_COUNT
