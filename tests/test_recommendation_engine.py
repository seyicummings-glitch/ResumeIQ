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
