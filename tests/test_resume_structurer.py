from app.services.resume_structurer import structure_resume, extract_contact_info


def test_structures_french_resume_sections():
    text = (
        "Jean Dupont\n"
        "Expérience Professionnelle\n"
        "Développeur Python chez Acme, 3 ans\n"
        "\n"
        "Compétences\n"
        "Python, FastAPI, PostgreSQL\n"
        "\n"
        "Formation\n"
        "Master Informatique, Université de Paris\n"
    )
    result = structure_resume(text)
    assert "python" in [s.lower() for s in result["skills"]]
    assert "Développeur Python" in result["experience"]
    assert "Master Informatique" in result["education"]


def test_structures_spanish_resume_sections():
    text = (
        "Ana García\n"
        "Experiencia Laboral\n"
        "Desarrolladora Python en Acme, 3 años\n"
        "\n"
        "Habilidades\n"
        "Python, FastAPI, PostgreSQL\n"
        "\n"
        "Educación\n"
        "Máster en Informática\n"
    )
    result = structure_resume(text)
    assert "python" in [s.lower() for s in result["skills"]]
    assert "Desarrolladora Python" in result["experience"]


def test_english_still_works():
    text = "Summary\nExperienced engineer.\n\nSkills\nPython, SQL\n"
    result = structure_resume(text)
    assert "python" in [s.lower() for s in result["skills"]]


def test_phone_detects_north_american_format():
    assert extract_contact_info("Call me at 555-123-4567.")["phone"] == "555-123-4567"


def test_phone_detects_international_formats_with_non_3_3_4_grouping():
    # French/Moroccan mobile grouping (2-2-2-2-2), not the old regex's rigid 3-3-4.
    assert extract_contact_info("Phone: +212 6 12 34 56 78")["phone"] is not None
    assert extract_contact_info("Tel: 06 12 34 56 78")["phone"] is not None
    # Turkish grouping.
    assert extract_contact_info("+90 532 123 45 67")["phone"] is not None


def test_phone_not_detected_when_absent():
    assert extract_contact_info("Experienced engineer with 5 years in the field.")["phone"] is None


def test_skills_section_with_extra_wording_is_recognized():
    text = "Summary\nEngineer.\n\nTechnical Skills & Tools\nPython, Docker\n\nExperience\nDid stuff.\n"
    result = structure_resume(text)
    assert "python" in [s.lower() for s in result["skills"]]


def test_experience_section_with_numbering_is_recognized():
    text = "1. Work Experience\nSenior Engineer at Acme, 3 years.\n\n2. Education\nBSc Computer Science\n"
    result = structure_resume(text)
    assert "Senior Engineer" in result["experience"]
    assert "BSc Computer Science" in result["education"]


def test_languages_and_references_sections_are_recognized():
    text = (
        "Summary\nEngineer.\n\n"
        "Skills\nPython\n\n"
        "Languages\nSpanish - Fluent\nFrench - Conversational\n\n"
        "References\nJane Doe, Manager at Acme, jane@acme.com\n"
    )
    result = structure_resume(text)
    assert "Spanish - Fluent" in result["languages"]
    assert "Jane Doe" in result["references"]


def test_short_sentence_mentioning_a_header_word_is_not_treated_as_a_header():
    # "...6 years of experience." is short enough to slip under the header-length cutoff, but
    # it's a sentence (ends in a period), not a header — must not be mistaken for "Experience".
    text = (
        "Jordan Mitchell\n\n"
        "Summary\n"
        "Marketing manager with 6 years of experience.\n\n"
        "Skills\n"
        "SEO, CRM, Negotiation\n\n"
        "Experience\n"
        "Senior Marketing Manager at Acme, 2022 - Present.\n"
    )
    result = structure_resume(text)
    assert result["summary"] == "Marketing manager with 6 years of experience."
    assert "Senior Marketing Manager" in result["experience"]


def test_long_line_mentioning_a_header_word_is_not_treated_as_a_header():
    text = (
        "Summary\n"
        "I have a strong education and years of experience building backend systems for clients.\n"
        "\nSkills\nPython\n"
    )
    result = structure_resume(text)
    # The long summary sentence mentions "education"/"experience" but must not be
    # mistaken for those section headers.
    assert "strong education" in result["summary"]
