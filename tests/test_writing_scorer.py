from app.services.writing_scorer import (
    score_action_verbs,
    score_quantification,
    score_conciseness,
    score_weak_language,
    calculate_writing_score,
)


def test_action_verbs_all_strong():
    bullets = ["Led a team of 5 engineers", "Built a new payments pipeline", "Improved latency by 30%"]
    result = score_action_verbs(bullets)
    assert result["action_verb_score"] == 30
    assert result["issues"] == []


def test_action_verbs_none_strong():
    bullets = ["Was part of a team", "Helped with various tasks"]
    result = score_action_verbs(bullets)
    assert result["action_verb_score"] == 0
    assert len(result["issues"]) == 1


def test_action_verbs_empty():
    result = score_action_verbs([])
    assert result["action_verb_score"] == 0
    assert len(result["issues"]) == 1


def test_quantification_high():
    bullets = ["Reduced costs by 40%", "Served 2M requests/day", "Cut deploy time from 20min to 5min"]
    result = score_quantification(bullets)
    assert result["quantification_score"] == 30


def test_quantification_low():
    bullets = ["Worked on backend systems", "Helped the team ship features"]
    result = score_quantification(bullets)
    assert result["quantification_score"] == 0
    assert len(result["issues"]) == 1


def test_conciseness_too_short():
    bullets = ["Did stuff", "Wrote code", "Fixed bugs"]
    result = score_conciseness(bullets)
    assert result["conciseness_score"] == 8


def test_conciseness_ideal():
    bullets = [
        "Led the migration of a monolithic service to microservices, reducing deploy time by 40 percent",
    ]
    result = score_conciseness(bullets)
    assert result["conciseness_score"] == 20


def test_weak_language_flagged():
    bullets = ["Responsible for maintaining the database", "Built a new API from scratch"]
    result = score_weak_language(bullets)
    assert result["weak_language_score"] == 10
    assert len(result["issues"]) == 1


def test_weak_language_none_flagged():
    bullets = ["Built a new API from scratch", "Led the migration effort"]
    result = score_weak_language(bullets)
    assert result["weak_language_score"] == 20
    assert result["issues"] == []


def test_calculate_writing_score_strong_resume():
    structured_data = {
        "experience": (
            "Led the migration of a monolithic service to microservices, reducing deploy time by 40 percent\n"
            "Built and maintained REST APIs serving 2 million requests per day\n"
            "Mentored 3 junior engineers and improved onboarding time by 25 percent"
        )
    }
    result = calculate_writing_score(structured_data)
    assert result["overall_writing_score"] == 100
    assert result["issues"] == []


def test_calculate_writing_score_weak_resume():
    structured_data = {
        "experience": "Responsible for various tasks\nHelped with stuff\nWorked on things",
    }
    result = calculate_writing_score(structured_data)
    assert result["overall_writing_score"] < 50
    assert len(result["issues"]) > 0


def test_calculate_writing_score_no_experience():
    result = calculate_writing_score({"experience": ""})
    assert result["overall_writing_score"] == 0
    assert result["bullet_count"] == 0
