from app.services.pdf_report import generate_analysis_pdf


SAMPLE_ANALYSIS = {
    "overall_match_score": 78.5,
    "skill_match": {
        "skill_score": 80.0,
        "matched_skills": ["python", "fastapi", "sql"],
        "missing_skills": ["docker", "kubernetes"],
    },
    "experience_match": {"experience_score": 70.0},
    "qualification_match": {"qualification_score": 85.0},
}


def test_generate_analysis_pdf_returns_valid_pdf_bytes():
    pdf_bytes = generate_analysis_pdf(SAMPLE_ANALYSIS, "resume.pdf", "Backend Engineer")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


def test_generate_analysis_pdf_handles_missing_skill_lists():
    analysis = {
        "overall_match_score": 40.0,
        "skill_match": {"skill_score": 40.0, "matched_skills": [], "missing_skills": []},
        "experience_match": {"experience_score": 30.0},
        "qualification_match": {"qualification_score": 50.0},
    }
    pdf_bytes = generate_analysis_pdf(analysis, "old_resume.docx", "Data Analyst")
    assert pdf_bytes.startswith(b"%PDF")


def test_generate_analysis_pdf_handles_empty_dict():
    pdf_bytes = generate_analysis_pdf({}, "resume.pdf", "Some Job")
    assert pdf_bytes.startswith(b"%PDF")
