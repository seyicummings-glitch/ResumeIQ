from app.services.interview_questions import (
    BEHAVIORAL_BASE,
    build_technical_questions,
    build_system_design_questions,
    build_role_questions,
    build_interview_questions,
)


def test_behavioral_base_has_three_fixed_questions():
    assert len(BEHAVIORAL_BASE) == 3
    ids = [q["id"] for q in BEHAVIORAL_BASE]
    assert ids == [101, 102, 103]
    for q in BEHAVIORAL_BASE:
        assert q["category"] == "Behavioral"
        assert q["question"] and q["tip"] and q["sample_answer"] and q["relevance"]


def test_technical_questions_depth_check_on_resume_skill():
    questions = build_technical_questions(missing_skills=[], resume_skills=["React", "CSS"])
    assert len(questions) == 1
    assert questions[0]["category"] == "Technical"
    assert "React" in questions[0]["question"]


def test_technical_questions_stops_after_first_depth_match():
    # Python appears after React in the scan order; only the first match (React) should be used.
    questions = build_technical_questions(missing_skills=[], resume_skills=["CSS", "React", "Python"])
    assert len(questions) == 1
    assert "React" in questions[0]["question"]


def test_technical_questions_no_depth_match_for_unrecognized_skills():
    questions = build_technical_questions(missing_skills=[], resume_skills=["Photoshop", "Excel"])
    assert questions == []


def test_technical_questions_missing_skill_specific_docker():
    questions = build_technical_questions(missing_skills=["Docker"], resume_skills=[])
    assert len(questions) == 1
    assert "Docker" in questions[0]["question"]
    assert "isn't on your current resume" in questions[0]["question"]


def test_technical_questions_missing_skill_generic_fallback():
    questions = build_technical_questions(missing_skills=["Cobol"], resume_skills=[])
    assert len(questions) == 1
    assert questions[0]["question"] == (
        "The job description requires Cobol, which isn't on your current resume. "
        "How would you approach getting up to speed?"
    )
    assert "Cobol" in questions[0]["relevance"]


def test_technical_questions_caps_at_four_and_covers_two_missing_skills():
    questions = build_technical_questions(
        missing_skills=["Docker", "Kubernetes", "TypeScript"],
        resume_skills=["React"],
    )
    # 1 depth-check (React) + 2 missing-skill questions (Docker, Kubernetes) capped at 4
    assert len(questions) == 3
    categories = {q["category"] for q in questions}
    assert categories == {"Technical"}


def test_technical_questions_unique_ids():
    questions = build_technical_questions(
        missing_skills=["Docker", "Kubernetes"],
        resume_skills=["React"],
    )
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))
    assert ids[0] == 200


def test_system_design_always_includes_url_shortener():
    questions = build_system_design_questions("Backend Engineer")
    ids = [q["id"] for q in questions]
    assert 302 in ids
    assert all(q["category"] == "System Design" and q["difficulty"] == "Hard" for q in questions)


def test_system_design_empty_for_a_non_software_engineering_title():
    assert build_system_design_questions("Head Chef") == []


def test_system_design_empty_when_profession_category_explicitly_non_technical():
    # Even with a title that would otherwise look ambiguous, an explicit
    # non-software-engineering profession_category always wins.
    assert build_system_design_questions("Backend Engineer", profession_category="culinary_hospitality") == []


def test_system_design_adds_payments_question_for_fintech_title():
    questions = build_system_design_questions("Senior Fintech Backend Engineer")
    ids = [q["id"] for q in questions]
    assert ids[0] == 301
    assert 302 in ids
    assert len(questions) == 2


def test_system_design_no_payments_question_for_generic_title():
    questions = build_system_design_questions("Backend Engineer")
    ids = [q["id"] for q in questions]
    assert 301 not in ids
    assert ids == [302]


def test_role_questions_senior_variant():
    questions = build_role_questions("Senior Backend Engineer")
    assert len(questions) == 1
    assert questions[0]["difficulty"] == "Hard"
    assert questions[0]["id"] == 402
    assert "mentor" in questions[0]["question"].lower()


def test_role_questions_default_variant():
    questions = build_role_questions("Backend Engineer")
    assert len(questions) == 1
    assert questions[0]["difficulty"] == "Medium"
    assert questions[0]["id"] == 402
    assert "on-call" in questions[0]["question"].lower()


def test_role_questions_generic_for_a_non_software_engineering_title():
    questions = build_role_questions("Head Chef")
    assert len(questions) == 1
    assert "on-call" not in questions[0]["question"].lower()
    assert "ownership" in questions[0]["relevance"].lower()


def test_role_questions_generic_when_profession_category_explicitly_non_technical():
    questions = build_role_questions("Backend Engineer", profession_category="culinary_hospitality")
    assert "on-call" not in questions[0]["question"].lower()


def test_build_interview_questions_orchestrates_all_sections():
    questions = build_interview_questions(
        missing_skills=["Docker"],
        resume_skills=["React"],
        jd_title="Senior Backend Engineer",
    )
    categories = [q["category"] for q in questions]
    assert categories.count("Behavioral") == 3
    assert "Technical" in categories
    assert "System Design" in categories
    assert "Role-Specific" in categories


def test_build_interview_questions_never_returns_system_design_for_a_chef():
    questions = build_interview_questions(
        missing_skills=["Food Safety"],
        resume_skills=["Menu Planning", "Knife Skills"],
        jd_title="Head Chef",
    )
    categories = [q["category"] for q in questions]
    assert "System Design" not in categories
    assert categories.count("Behavioral") == 3  # still gets the profession-neutral base
    role_question = next(q for q in questions if q["category"] == "Role-Specific")
    assert "on-call" not in role_question["question"].lower()
