from app.services.admin_analytics import compute_top_missing_skills


def test_compute_top_missing_skills_counts_and_orders():
    result_jsons = [
        {"skill_match": {"missing_skills": ["aws", "docker"]}},
        {"skill_match": {"missing_skills": ["aws", "kubernetes"]}},
        {"skill_match": {"missing_skills": ["docker"]}},
        None,
        {"skill_match": {}},
        {},
    ]
    result = compute_top_missing_skills(result_jsons, top_n=10)

    assert result[0] == {"skill": "aws", "count": 2}
    assert result[1] == {"skill": "docker", "count": 2}
    assert {"skill": "kubernetes", "count": 1} in result
    assert len(result) == 3


def test_compute_top_missing_skills_respects_top_n():
    result_jsons = [{"skill_match": {"missing_skills": [f"skill{i}"]}} for i in range(15)]
    result = compute_top_missing_skills(result_jsons, top_n=10)
    assert len(result) == 10


def test_compute_top_missing_skills_handles_empty_input():
    assert compute_top_missing_skills([], top_n=10) == []
    assert compute_top_missing_skills(None, top_n=10) == []
