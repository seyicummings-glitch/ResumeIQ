from app.services.job_description_parser import (
    extract_required_skills,
    extract_experience_level,
    extract_qualifications,
    parse_job_description,
)


def test_extract_required_skills_tech():
    text = "We need someone skilled in Python, FastAPI, and PostgreSQL."
    skills = extract_required_skills(text)
    assert "python" in skills


def test_extract_required_skills_law():
    text = "Looking for an attorney experienced in litigation and courtroom advocacy."
    skills = extract_required_skills(text)
    assert "litigation" in skills or "attorney" in skills or "courtroom" in skills


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


def test_extract_qualifications_law():
    text = "Requires a J.D. degree and active bar license."
    quals = extract_qualifications(text)
    assert "j.d." in quals or "jd" in quals


def test_parse_job_description_full():
    text = "Software Engineer with 3+ years of experience in Python and Docker. Bachelor's degree required."
    result = parse_job_description(text)
    assert result["experience_level"] == "3+ years"
    assert "bachelor" in result["qualifications"]