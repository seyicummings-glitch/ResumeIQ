from app.services.keyword_analyzer import analyze_keywords


def test_matched_and_missing_split():
    resume_text = "Experienced with Python and Docker."
    jd_keywords = ["python", "docker", "kubernetes"]
    result = analyze_keywords(resume_text, jd_keywords)
    assert set(result["matched_keywords"]) == {"python", "docker"}
    assert result["missing_keywords"] == ["kubernetes"]


def test_frequency_counts_multiple_occurrences():
    resume_text = "Python developer. Built Python tools. Python everywhere."
    jd_keywords = ["python"]
    result = analyze_keywords(resume_text, jd_keywords)
    assert result["keyword_frequency"]["python"] == 3


def test_word_boundary_does_not_match_substring():
    resume_text = "Experienced JavaScript developer."
    jd_keywords = ["java"]
    result = analyze_keywords(resume_text, jd_keywords)
    assert result["keyword_frequency"]["java"] == 0
    assert "java" in result["missing_keywords"]
