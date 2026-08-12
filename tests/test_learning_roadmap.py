from app.services.learning_roadmap import (
    STAGE_NAMES,
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


def test_detect_profession_category_falls_back_to_general_when_nothing_matches():
    assert detect_profession_category(None, None, [], []) == "general"
    assert detect_profession_category("Yoga Instructor", None, ["Mindfulness"], []) == "general"


def test_detect_profession_category_uses_resume_text_when_other_signals_are_thin():
    result = detect_profession_category(
        None, None, [], [], resume_text="Led quarterly financial reporting and audit preparation for a mid-size firm."
    )
    assert result == "accounting"


# --- Profession-aware roadmap building --------------------------------------

def test_build_roadmap_always_returns_four_fixed_stages_in_order():
    result = build_roadmap([], [])
    stages = result["stages"]
    assert [s["stage"] for s in stages] == STAGE_NAMES


def test_build_roadmap_never_defaults_to_software_engineering_for_business_resume():
    result = build_roadmap(
        missing_skills=["Financial Modeling", "Stakeholder Management"],
        resume_skills=["Strategic Planning", "Business Analysis"],
        target_role="Business Administration",
    )
    foundation_titles = [t["title"] for t in result["stages"][0]["topics"]]
    job_ready_titles = [t["title"] for t in result["stages"][3]["topics"]]

    assert "Version control with Git" not in foundation_titles
    assert "Core data structures & algorithms" not in foundation_titles
    assert "System design & architecture fundamentals" not in job_ready_titles
    assert result["detected_profession"] == "Business Administration"


def test_build_roadmap_marketing_resume_gets_marketing_foundation_topics():
    result = build_roadmap(
        missing_skills=["Google Analytics", "Content Marketing"],
        resume_skills=["SEO", "Social Media Marketing"],
    )
    foundation_titles = [t["title"] for t in result["stages"][0]["topics"]]
    assert any("marketing" in title.lower() for title in foundation_titles)
    assert "Version control with Git" not in foundation_titles


def test_build_roadmap_software_engineering_resume_still_gets_swe_topics():
    # The old behavior is correct when the candidate genuinely IS a software
    # engineer — this isn't about banning SWE content, just not defaulting to it.
    result = build_roadmap(
        missing_skills=["Docker", "Kubernetes"],
        resume_skills=["Python", "React"],
        target_role="Backend Engineer",
        industry="Tech",
    )
    foundation_titles = [t["title"] for t in result["stages"][0]["topics"]]
    assert "Version control with Git" in foundation_titles


def test_build_roadmap_foundation_and_job_ready_depend_on_detected_category_not_missing_skills():
    # Same profession signal (a fixed target_role), different missing_skills --
    # Foundation/Job Ready should stay stable since they're keyed off detected
    # category, not the specific gaps (unlike Intermediate/Advanced, which do
    # vary with missing_skills by design).
    result_a = build_roadmap([], [], target_role="Backend Engineer")
    result_b = build_roadmap(["Docker", "Kubernetes", "GraphQL"], [], target_role="Backend Engineer")
    foundation_a = [t["title"] for t in result_a["stages"][0]["topics"]]
    foundation_b = [t["title"] for t in result_b["stages"][0]["topics"]]
    assert foundation_a == foundation_b


def test_build_roadmap_splits_missing_skills_between_intermediate_and_advanced():
    skills = ["Docker", "Kubernetes", "GraphQL", "AWS"]
    result = build_roadmap(skills, [])
    intermediate_titles = [t["title"] for t in result["stages"][1]["topics"]]
    advanced_titles = [t["title"] for t in result["stages"][2]["topics"]]

    assert intermediate_titles == ["Docker", "Kubernetes"]
    assert advanced_titles == ["GraphQL", "AWS"]


def test_build_roadmap_advanced_gap_topics_are_critical_priority():
    result = build_roadmap(["Docker", "GraphQL"], [])
    advanced_topics = result["stages"][2]["topics"]
    assert all(t["priority"] == "critical" for t in advanced_topics)


def test_build_roadmap_topic_shape_has_all_required_fields():
    result = build_roadmap(["Docker"], [])
    topic = result["stages"][1]["topics"][0]
    required_fields = {
        "title", "category", "why_it_matters", "current_gap", "learning_objectives", "milestones", "resources",
        "projects", "exercises", "quiz", "estimated_hours", "priority",
    }
    assert required_fields <= set(topic.keys())
    assert len(topic["resources"]) == 3


def test_build_roadmap_topic_milestones_and_quiz_are_well_formed():
    result = build_roadmap(["Docker"], [])
    for stage in result["stages"]:
        for topic in stage["topics"]:
            assert {"beginner", "intermediate", "advanced"} <= set(topic["milestones"].keys())
            assert len(topic["quiz"]) >= 2
            for question in topic["quiz"]:
                assert len(question["options"]) == 4
                assert 0 <= question["correct_index"] < 4


def test_build_roadmap_does_not_mutate_shared_fixed_topic_lists():
    # Foundation/Job Ready topics are shared module-level lists reused across every call —
    # calling build_roadmap() repeatedly must not leak mutated state into those shared dicts.
    from app.services.learning_roadmap import _FOUNDATION_BANKS

    build_roadmap(["Docker"], [], target_role="Backend Engineer")
    build_roadmap(["Kubernetes"], [], target_role="Backend Engineer")
    assert "current_gap" not in _FOUNDATION_BANKS["software_engineering"][0]


def test_build_roadmap_stage_shape_has_required_fields():
    result = build_roadmap(["Docker"], [])
    for stage in result["stages"]:
        assert {"stage", "description", "estimated_duration", "milestone", "topics"} <= set(stage.keys())


def test_build_roadmap_with_no_missing_skills_still_fills_intermediate_and_advanced():
    # No gaps identified — falls back to reinforcing resume skills rather than an empty stage.
    result = build_roadmap([], ["Python", "React", "SQL", "Docker"])
    assert len(result["stages"][1]["topics"]) > 0
    assert len(result["stages"][2]["topics"]) > 0


def test_build_roadmap_detected_profession_prefers_target_role_over_category_label():
    result = build_roadmap([], [], target_role="Senior Marketing Manager")
    assert result["detected_profession"] == "Senior Marketing Manager"


def test_build_roadmap_detected_profession_falls_back_to_category_label_when_no_target_role():
    result = build_roadmap(["Google Analytics"], ["SEO"])
    assert result["detected_profession"] == PROFESSION_LABELS["marketing"]
