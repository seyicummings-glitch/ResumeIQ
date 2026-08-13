from app.services.learning_roadmap import (
    get_resources,
    get_resource_type,
    get_provider,
    build_roadmap,
    detect_profession_category,
    PROFESSION_LABELS,
)


def test_get_resources_known_skill_returns_three_named_resources():
    resources = get_resources("Docker")
    assert len(resources) == 3
    assert all({"name", "type", "provider"} <= set(r.keys()) for r in resources)
    assert any("Docker" in r["name"] for r in resources)


def test_get_resources_unknown_skill_falls_back_to_generic():
    resources = get_resources("Cobol")
    assert len(resources) == 3
    assert "Cobol" in resources[0]["name"]


def test_get_resources_case_insensitive():
    assert get_resources("KUBERNETES") == get_resources("kubernetes")


def test_get_resource_type_cert():
    assert get_resource_type("AWS") == "Cert"
    assert get_resource_type("Terraform Associate") == "Cert"


def test_get_resource_type_default_course():
    assert get_resource_type("React") == "Course"


def test_get_provider_known_and_fallback():
    assert get_provider("Docker") == "Docker + Udemy"
    assert get_provider("Cobol") == "Multiple providers"


# --- Profession detection ---------------------------------------------------

def test_detect_profession_category_software_engineering():
    assert detect_profession_category("Backend Engineer", "Tech", ["Python", "Docker"], ["Kubernetes"]) == "software_engineering"


def test_detect_profession_category_business_administration():
    assert detect_profession_category(
        "Business Administration", None, ["Strategic Planning", "Stakeholder Management"], ["Project Management"]
    ) == "business_administration"


def test_detect_profession_category_marketing():
    assert detect_profession_category(
        None, None, ["SEO", "Social Media Marketing"], ["Google Analytics", "Content Marketing"]
    ) == "marketing"


def test_detect_profession_category_accounting():
    assert detect_profession_category(
        "Staff Accountant", None, ["Bookkeeping", "GAAP"], ["Taxation", "Auditing"]
    ) == "accounting"


def test_detect_profession_category_healthcare():
    assert detect_profession_category(
        "Registered Nurse", None, ["Patient Care", "Nursing"], ["EHR", "HIPAA Compliance"]
    ) == "healthcare"


def test_detect_profession_category_falls_back_to_general_when_nothing_matches():
    assert detect_profession_category(None, None, [], []) == "general"
    assert detect_profession_category("Yoga Instructor", None, ["Mindfulness"], []) == "general"


def test_detect_profession_category_uses_resume_text_when_other_signals_are_thin():
    result = detect_profession_category(
        None, None, [], [], resume_text="Led quarterly financial reporting and audit preparation for a mid-size firm."
    )
    assert result == "accounting"


# --- Roadmap building is purely missing-skill-driven -------------------------
#
# No stage is ever filled from a fixed, pre-written topic list — every topic
# in every stage must trace back to an entry in the missing_skills the caller
# passed in. Profession detection only affects labeling/grouping, never which
# topics appear.

def _all_titles(result: dict) -> list[str]:
    return [t["title"] for stage in result["stages"] for t in stage["topics"]]


def test_build_roadmap_topics_are_exactly_the_missing_skills_no_more_no_less():
    skills = ["Financial Modeling", "Stakeholder Management", "Six Sigma", "Budget Management"]
    result = build_roadmap(skills, ["Strategic Planning"], target_role="Business Administration")
    assert sorted(_all_titles(result)) == sorted(skills)


def test_build_roadmap_never_shows_programming_skills_for_a_business_resume():
    result = build_roadmap(
        missing_skills=["Financial Modeling", "Stakeholder Management"],
        resume_skills=["Strategic Planning", "Business Analysis"],
        target_role="Business Administration",
    )
    titles = _all_titles(result)
    assert "GitHub" not in titles
    assert "React" not in titles
    assert "Docker" not in titles
    assert "CI/CD" not in titles
    assert "TypeScript" not in titles
    assert result["detected_profession"] == "Business Administration"


def test_build_roadmap_marketing_resume_gets_only_marketing_gap_topics():
    result = build_roadmap(
        missing_skills=["Google Analytics", "Content Marketing"],
        resume_skills=["SEO", "Social Media Marketing"],
    )
    titles = _all_titles(result)
    assert set(titles) == {"Google Analytics", "Content Marketing"}
    assert "Docker" not in titles
    assert "Version control with Git" not in titles


def test_build_roadmap_healthcare_resume_gets_only_healthcare_gap_topics():
    result = build_roadmap(
        missing_skills=["EHR", "HIPAA Compliance"],
        resume_skills=["Patient Care", "Nursing"],
        target_role="Registered Nurse",
    )
    titles = _all_titles(result)
    assert set(titles) == {"EHR", "HIPAA Compliance"}
    assert result["detected_profession"] == "Registered Nurse"


def test_build_roadmap_software_engineering_resume_gets_its_own_actual_gaps():
    # Not "banned" content — just never assumed. A genuine SWE gap list produces
    # genuine SWE topics because that's what was actually passed in, not because
    # of any profession-keyed lookup table.
    result = build_roadmap(
        missing_skills=["Docker", "Kubernetes"],
        resume_skills=["Python", "React"],
        target_role="Backend Engineer",
        industry="Tech",
    )
    assert set(_all_titles(result)) == {"Docker", "Kubernetes"}


def test_build_roadmap_two_different_missing_skill_lists_produce_different_roadmaps():
    result_a = build_roadmap(["Docker", "Kubernetes"], [], target_role="Backend Engineer")
    result_b = build_roadmap(["GraphQL", "Terraform", "Redis"], [], target_role="Backend Engineer")
    assert _all_titles(result_a) != _all_titles(result_b)


def test_build_roadmap_distributes_gaps_across_up_to_four_stages_in_order():
    skills = ["Docker", "Kubernetes", "GraphQL", "AWS", "Terraform"]
    result = build_roadmap(skills, [])
    stage_names = [s["stage"] for s in result["stages"]]
    # Ordered subsequence of the canonical stage order, never out of order.
    canonical_order = ["Foundation", "Intermediate", "Advanced", "Job Ready"]
    assert stage_names == [name for name in canonical_order if name in stage_names]
    # every gap appears exactly once across all stages
    assert sorted(_all_titles(result)) == sorted(skills)


def test_build_roadmap_does_not_fabricate_empty_stages_for_short_gap_lists():
    result = build_roadmap(["Docker"], [])
    assert len(result["stages"]) == 1
    assert result["stages"][0]["topics"][0]["title"] == "Docker"


def test_build_roadmap_later_stage_gaps_are_higher_priority():
    skills = ["Docker", "Kubernetes", "GraphQL", "AWS"]
    result = build_roadmap(skills, [])
    priorities = [stage["topics"][0]["priority"] for stage in result["stages"]]
    # priority never decreases from Foundation through Job Ready
    order = {"medium": 0, "high": 1, "critical": 2}
    assert all(order[priorities[i]] <= order[priorities[i + 1]] for i in range(len(priorities) - 1))


def test_build_roadmap_topic_shape_has_all_required_fields():
    result = build_roadmap(["Docker"], [])
    topic = result["stages"][0]["topics"][0]
    required_fields = {
        "title", "category", "why_it_matters", "current_gap", "learning_objectives", "milestones", "resources",
        "projects", "exercises", "quiz", "estimated_hours", "priority",
    }
    assert required_fields <= set(topic.keys())
    assert len(topic["resources"]) == 3


def test_build_roadmap_topic_milestones_and_quiz_are_well_formed():
    result = build_roadmap(["Docker", "Kubernetes", "GraphQL", "AWS"], [])
    for stage in result["stages"]:
        for topic in stage["topics"]:
            assert {"beginner", "intermediate", "advanced"} <= set(topic["milestones"].keys())
            assert len(topic["quiz"]) >= 2
            for question in topic["quiz"]:
                assert len(question["options"]) == 4
                assert 0 <= question["correct_index"] < 4


def test_build_roadmap_stage_shape_has_required_fields():
    result = build_roadmap(["Docker"], [])
    for stage in result["stages"]:
        assert {"stage", "description", "estimated_duration", "milestone", "topics"} <= set(stage.keys())


def test_build_roadmap_deduplicates_missing_skills_case_insensitively():
    result = build_roadmap(["Docker", "docker", "DOCKER "], [])
    assert _all_titles(result) == ["Docker"]


def test_build_roadmap_with_no_missing_skills_returns_honest_status_topic_not_fake_skills():
    result = build_roadmap([], ["Python", "React", "SQL", "Docker"])
    assert len(result["stages"]) == 1
    topic = result["stages"][0]["topics"][0]
    assert topic["title"] == "No critical skill gaps identified"
    assert "already covers" in topic["why_it_matters"]


def test_build_roadmap_with_no_missing_skills_and_no_resume_context_says_so_honestly():
    result = build_roadmap([], [], target_role="Product Manager")
    topic = result["stages"][0]["topics"][0]
    assert topic["title"] == "No critical skill gaps identified"
    assert "Save a resume" in topic["why_it_matters"]


def test_build_roadmap_detected_profession_prefers_target_role_over_category_label():
    result = build_roadmap(["Google Analytics"], [], target_role="Senior Marketing Manager")
    assert result["detected_profession"] == "Senior Marketing Manager"


def test_build_roadmap_detected_profession_falls_back_to_category_label_when_no_target_role():
    result = build_roadmap(["Google Analytics"], ["SEO"])
    assert result["detected_profession"] == PROFESSION_LABELS["marketing"]
