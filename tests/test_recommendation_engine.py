from app.services.recommendation_engine import rank_jobs_for_resume


def test_ranks_better_matching_job_higher():
    resume_text = "5 years experience. Python, FastAPI, PostgreSQL. Bachelor's degree."
    resume_skills = ["python", "fastapi", "postgresql"]
    jobs = [
        {"id": 1, "title": "Backend Engineer", "content": "Need Python, FastAPI, PostgreSQL, 3+ years experience, bachelor's degree required."},
        {"id": 2, "title": "Frontend Engineer", "content": "Need React, CSS, Figma, 5+ years experience."},
    ]
    ranked = rank_jobs_for_resume(resume_text, resume_skills, jobs)
    assert ranked[0]["job_description_id"] == 1
    assert ranked[0]["overall_match_score"] >= ranked[1]["overall_match_score"]


def test_empty_job_list_returns_empty():
    assert rank_jobs_for_resume("some text", ["python"], []) == []


def test_github_languages_add_bonus_to_ranking():
    resume_text = "5 years experience. Python, FastAPI."
    resume_skills = ["python", "fastapi"]
    jobs = [
        {"id": 1, "title": "Backend Engineer", "content": "Need Python, FastAPI, 3+ years experience."},
    ]
    ranked = rank_jobs_for_resume(resume_text, resume_skills, jobs, github_languages=["Python", "FastAPI"])
    assert "github_match" in ranked[0]
    assert ranked[0]["github_match"]["github_bonus_score"] > 0
    assert set(ranked[0]["github_match"]["matched_languages"]) == {"python", "fastapi"}
