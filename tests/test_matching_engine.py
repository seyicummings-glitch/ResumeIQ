from app.services.matching_engine import calculate_github_bonus, calculate_overall_match


def test_github_bonus_basic_overlap():
    result = calculate_github_bonus(["Python", "JavaScript"], ["python", "docker"])
    assert result["github_bonus_score"] == 50.0
    assert result["matched_languages"] == ["python"]


def test_github_bonus_no_required_skills():
    result = calculate_github_bonus(["Python"], [])
    assert result["github_bonus_score"] == 0
    assert result["matched_languages"] == []


def test_overall_match_without_github_unchanged():
    result = calculate_overall_match(
        resume_text="5 years experience. Python, FastAPI.",
        resume_skills=["python", "fastapi"],
        jd_required_skills=["python", "fastapi"],
        jd_experience_level="3+ years",
        jd_qualifications=[]
    )
    assert "github_match" not in result
    assert result["overall_match_score"] > 0


def test_overall_match_with_github_adds_bonus_component():
    result = calculate_overall_match(
        resume_text="5 years experience. Python, FastAPI.",
        resume_skills=["python", "fastapi"],
        jd_required_skills=["python", "fastapi"],
        jd_experience_level="3+ years",
        jd_qualifications=[],
        github_languages=["Python", "FastAPI"]
    )
    assert "github_match" in result
    assert result["github_match"]["github_bonus_score"] == 100.0
