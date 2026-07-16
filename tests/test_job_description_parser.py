from app.services.job_description_parser import (
    extract_required_skills,
    extract_experience_level,
    extract_qualifications,
    parse_job_description,
)


def test_extract_required_skills():
    text = "We need someone skilled in Python, FastAPI, and PostgreSQL."
    skills = extract_required_skills(text)
    assert "python" in skills
    assert "fastapi" in skills
    assert "postgresql" in skills


def test_extract_experience_level():
    text = "Looking for a candidate with 5+ years of experience."
    result = extract_experience_level(text)
    assert result == "5+ years"


def test_extract_experience_level_not_specified():
    text = "No experience requirement mentioned here."
    result = extract_experience_level(text)
    assert result == "Not specified"


def test_extract_qualifications():
    text = "Must have a Bachelor's degree in Computer Science."
    quals = extract_qualifications(text)
    assert "bachelor" in quals
    assert "degree" in quals


def test_parse_job_description_full():
    text = "Software Engineer with 3+ years of experience in Python and Docker. Bachelor's degree required."
    result = parse_job_description(text)
    assert "python" in result["required_skills"]
    assert result["experience_level"] == "3+ years"
    assert "bachelor" in result["qualifications"]