from app.services.learning_roadmap import (
    STAGE_NAMES,
    get_resources,
    get_resource_type,
    get_provider,
    build_roadmap,
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


def test_build_roadmap_always_returns_four_fixed_stages_in_order():
    result = build_roadmap([], [])
    stages = result["stages"]
    assert [s["stage"] for s in stages] == STAGE_NAMES


def test_build_roadmap_foundation_and_job_ready_are_evergreen():
    # Foundation and Job Ready don't depend on missing_skills at all.
    result_a = build_roadmap([], [])
    result_b = build_roadmap(["Docker", "Kubernetes", "GraphQL"], ["Python"])
    foundation_a = [t["title"] for t in result_a["stages"][0]["topics"]]
    foundation_b = [t["title"] for t in result_b["stages"][0]["topics"]]
    assert foundation_a == foundation_b

    job_ready_a = [t["title"] for t in result_a["stages"][3]["topics"]]
    job_ready_b = [t["title"] for t in result_b["stages"][3]["topics"]]
    assert job_ready_a == job_ready_b


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
        "title", "why_it_matters", "learning_objectives", "resources",
        "projects", "exercises", "estimated_hours", "priority",
    }
    assert required_fields <= set(topic.keys())
    assert len(topic["resources"]) == 3


def test_build_roadmap_stage_shape_has_required_fields():
    result = build_roadmap(["Docker"], [])
    for stage in result["stages"]:
        assert {"stage", "description", "estimated_duration", "milestone", "topics"} <= set(stage.keys())


def test_build_roadmap_with_no_missing_skills_still_fills_intermediate_and_advanced():
    # No gaps identified — falls back to reinforcing resume skills rather than an empty stage.
    result = build_roadmap([], ["Python", "React", "SQL", "Docker"])
    assert len(result["stages"][1]["topics"]) > 0
    assert len(result["stages"][2]["topics"]) > 0
