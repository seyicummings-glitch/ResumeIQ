from app.services.ats_scorer import (
    score_contact_completeness,
    score_section_completeness,
    score_skills_detected,
    score_text_extraction_health,
    score_file_format_risk,
    calculate_ats_score,
)


def test_contact_completeness_full():
    contact_info = {"email": "a@b.com", "phone": "555-123-4567", "linkedin": "linkedin.com/in/a"}
    result = score_contact_completeness(contact_info)
    assert result["contact_score"] == 15
    assert result["issues"] == []


def test_contact_completeness_empty():
    result = score_contact_completeness({"email": None, "phone": None, "linkedin": None})
    assert result["contact_score"] == 0
    assert len(result["issues"]) == 3


def test_contact_completeness_email_only():
    result = score_contact_completeness({"email": "a@b.com", "phone": None, "linkedin": None})
    assert result["contact_score"] == 8


def test_section_completeness_all_present():
    structured_data = {
        "experience": "some experience",
        "education": "some education",
        "skills": ["python"],
        "summary": "a summary",
        "certifications": "a cert",
        "projects": "a project",
    }
    result = score_section_completeness(structured_data)
    assert result["section_score"] == 25
    assert result["issues"] == []


def test_section_completeness_none_present():
    structured_data = {
        "experience": "",
        "education": "",
        "skills": [],
        "summary": "",
        "certifications": "",
        "projects": "",
    }
    result = score_section_completeness(structured_data)
    assert result["section_score"] == 0
    assert len(result["issues"]) == 6


def test_section_completeness_only_experience():
    structured_data = {
        "experience": "some experience",
        "education": "",
        "skills": [],
        "summary": "",
        "certifications": "",
        "projects": "",
    }
    result = score_section_completeness(structured_data)
    assert result["section_score"] == 8


def test_skills_detected_none():
    result = score_skills_detected([])
    assert result["skills_score"] == 0


def test_skills_detected_few():
    result = score_skills_detected(["python", "sql", "docker"])
    assert result["skills_score"] == 10


def test_skills_detected_moderate():
    result = score_skills_detected(["python", "sql", "docker", "aws", "react", "fastapi", "git"])
    assert result["skills_score"] == 15


def test_skills_detected_many():
    skills = ["python", "sql", "docker", "aws", "react", "fastapi", "git", "linux", "ci/cd", "kubernetes", "postgres", "redis"]
    result = score_skills_detected(skills)
    assert result["skills_score"] == 20


def test_text_extraction_health_near_empty():
    result = score_text_extraction_health("short")
    assert result["extraction_score"] == 0


def test_text_extraction_health_short():
    result = score_text_extraction_health("x" * 200)
    assert result["extraction_score"] == 10


def test_text_extraction_health_moderate():
    result = score_text_extraction_health("x" * 1000)
    assert result["extraction_score"] == 20


def test_text_extraction_health_full():
    result = score_text_extraction_health("x" * 2000)
    assert result["extraction_score"] == 25


def test_file_format_risk_docx_best():
    result = score_file_format_risk("resume.docx")
    assert result["format_score"] == 15
    assert result["issues"] == []


def test_file_format_risk_image_worst():
    result = score_file_format_risk("resume.png")
    assert result["format_score"] == 0
    assert len(result["issues"]) == 1


def test_calculate_ats_score_strong_resume():
    structured_data = {
        "contact_info": {"email": "a@b.com", "phone": "555-123-4567", "linkedin": "linkedin.com/in/a"},
        "experience": "some experience",
        "education": "some education",
        "skills": ["python", "sql", "docker", "aws", "react", "fastapi", "git", "linux", "ci/cd", "kubernetes"],
        "summary": "a summary",
        "certifications": "a cert",
        "projects": "a project",
    }
    result = calculate_ats_score("resume.docx", "x" * 2000, structured_data)
    assert result["overall_ats_score"] == 100
    assert result["issues"] == []


def test_calculate_ats_score_weak_resume():
    structured_data = {
        "contact_info": {"email": None, "phone": None, "linkedin": None},
        "experience": "",
        "education": "",
        "skills": [],
        "summary": "",
        "certifications": "",
        "projects": "",
    }
    result = calculate_ats_score("resume.png", "short", structured_data)
    assert result["overall_ats_score"] == 0
    assert len(result["issues"]) > 5
