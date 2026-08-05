import json
from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.skill_assessment_ai import (
    DEFAULT_TOTAL_COUNT,
    MAX_TOTAL_COUNT,
    MIN_TOTAL_COUNT,
    distribute_counts,
    generate_assessment_questions,
    grade_assessment_answers,
)


def _gemini_quota_error():
    return genai_errors.ClientError(
        429,
        {"error": {"code": 429, "message": "quota exceeded", "status": "RESOURCE_EXHAUSTED", "details": []}},
        None,
    )


def _mock_groq_response(payload: dict) -> Mock:
    response = Mock()
    response.choices = [Mock(message=Mock(content=json.dumps(payload)))]
    return response


def _hard_question(i, category="Python"):
    return {"category": category, "difficulty": "advanced", "question": f"Question {i}?", "expected_answer_points": f"Point {i}"}


def _soft_question(i, category="Leadership"):
    return {"category": category, "question": f"Question {i}?", "expected_answer_points": f"Point {i}"}


def _valid_payload(counts):
    return {
        "technical_questions": [_hard_question(i) for i in range(counts["technical"])],
        "scenario_questions": [_soft_question(i) for i in range(counts["scenario"])],
        "problem_solving_questions": [_hard_question(i) for i in range(counts["problem_solving"])],
        "behavioral_questions": [_soft_question(i) for i in range(counts["behavioral"])],
    }


def test_distribute_counts_default_matches_original_ratio():
    counts = distribute_counts(DEFAULT_TOTAL_COUNT)
    assert counts == {"technical": 6, "scenario": 3, "problem_solving": 3, "behavioral": 3}
    assert sum(counts.values()) == DEFAULT_TOTAL_COUNT


def test_distribute_counts_always_sums_to_total():
    for total in range(MIN_TOTAL_COUNT, MAX_TOTAL_COUNT + 1):
        counts = distribute_counts(total)
        assert sum(counts.values()) == total, f"failed for total={total}"


def test_distribute_counts_every_category_has_at_least_one():
    for total in range(MIN_TOTAL_COUNT, MAX_TOTAL_COUNT + 1):
        counts = distribute_counts(total)
        assert all(v >= 1 for v in counts.values()), f"failed for total={total}"


def test_distribute_counts_clamps_out_of_range():
    assert sum(distribute_counts(1).values()) == MIN_TOTAL_COUNT
    assert sum(distribute_counts(1000).values()) == MAX_TOTAL_COUNT


def test_generate_no_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [])
    assert result is None


def test_generate_ai_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [], ai_enabled=False)
    assert result is None


@patch("app.services.skill_assessment_ai.genai.Client")
def test_generate_successful_call_returns_default_counts(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(_valid_payload(distribute_counts(DEFAULT_TOTAL_COUNT)))
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [])
    assert result is not None
    total = sum(len(result[k]) for k in ["technical_questions", "scenario_questions", "problem_solving_questions", "behavioral_questions"])
    assert total == DEFAULT_TOTAL_COUNT


@patch("app.services.skill_assessment_ai.genai.Client")
def test_generate_respects_custom_total_count(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    counts = distribute_counts(10)
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(_valid_payload(counts))
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [], total_count=10)
    assert result is not None
    assert len(result["technical_questions"]) == counts["technical"]
    total = sum(len(result[k]) for k in ["technical_questions", "scenario_questions", "problem_solving_questions", "behavioral_questions"])
    assert total == 10


@patch("app.services.skill_assessment_ai.genai.Client")
def test_generate_wrong_count_in_any_category_returns_none(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    bad_payload = _valid_payload(distribute_counts(DEFAULT_TOTAL_COUNT))
    bad_payload["behavioral_questions"] = bad_payload["behavioral_questions"][:-1]
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(bad_payload)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [])
    assert result is None


@patch("app.services.skill_assessment_ai.genai.Client")
def test_generate_api_error_returns_none(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = RuntimeError("boom")
    mock_client_cls.return_value = mock_client

    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [])
    assert result is None


@patch("app.services.skill_assessment_ai.genai.Client")
def test_target_role_takes_priority_over_resume_in_prompt(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(_valid_payload(distribute_counts(DEFAULT_TOTAL_COUNT)))
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    generate_assessment_questions(
        "Backend Developer", "Fintech", "senior", "resume mentions only frontend work", ["React"], [], "jd", []
    )
    sent_contents = mock_client_cls.return_value.models.generate_content.call_args.kwargs["contents"]
    assert "Backend Developer" in sent_contents
    assert "Fintech" in sent_contents
    assert "PRIMARY driver" in sent_contents


@patch("app.services.skill_assessment_ai.genai.Client")
def test_recent_questions_included_in_avoid_list(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(_valid_payload(distribute_counts(DEFAULT_TOTAL_COUNT)))
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    generate_assessment_questions(
        "Backend Developer", "Fintech", "senior", "resume", ["Python"], ["Docker"], "jd",
        recent_questions=["What is a REST API?"],
    )
    sent_contents = mock_client_cls.return_value.models.generate_content.call_args.kwargs["contents"]
    assert "What is a REST API?" in sent_contents
    assert "genuinely fresh set" in sent_contents


def test_grade_no_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = grade_assessment_answers([{"id": 1, "type": "technical", "question": "q", "expected_answer_points": "p", "answer": "a"}])
    assert result is None


def test_grade_empty_items_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert grade_assessment_answers([]) is None


@patch("app.services.skill_assessment_ai.genai.Client")
def test_grade_successful_call_returns_results_for_every_item(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    items = [
        {"id": 1, "type": "technical", "question": "q1", "expected_answer_points": "p1", "answer": "a1"},
        {"id": 2, "type": "behavioral", "question": "q2", "expected_answer_points": "p2", "answer": "a2"},
    ]
    payload = {
        "results": [
            {"question_id": 1, "score": 90, "is_correct": True, "explanation": "Correct.", "correct_answer_or_improvement": "Ideal answer."},
            {"question_id": 2, "score": 20, "is_correct": False, "explanation": "Off-topic.", "correct_answer_or_improvement": "Be more specific."},
        ]
    }
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(payload)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = grade_assessment_answers(items)
    assert result is not None
    assert len(result) == 2
    assert result[0]["score"] == 90
    assert result[1]["is_correct"] is False


@patch("app.services.skill_assessment_ai.genai.Client")
def test_grade_mismatched_result_count_returns_none(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    items = [
        {"id": 1, "type": "technical", "question": "q1", "expected_answer_points": "p1", "answer": "a1"},
        {"id": 2, "type": "behavioral", "question": "q2", "expected_answer_points": "p2", "answer": "a2"},
    ]
    payload = {"results": [{"question_id": 1, "score": 90, "is_correct": True, "explanation": "x", "correct_answer_or_improvement": "y"}]}
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(payload)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = grade_assessment_answers(items)
    assert result is None


@patch("app.services.skill_assessment_ai.genai.Client")
def test_grade_api_error_returns_none(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = RuntimeError("boom")
    mock_client_cls.return_value = mock_client

    items = [{"id": 1, "type": "technical", "question": "q1", "expected_answer_points": "p1", "answer": "a1"}]
    result = grade_assessment_answers(items)
    assert result is None


# --- Groq fallback -------------------------------------------------------


@patch("app.services.skill_assessment_ai.groq_client")
@patch("app.services.skill_assessment_ai.genai.Client")
def test_generate_quota_error_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    counts = distribute_counts(DEFAULT_TOTAL_COUNT)
    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response(_valid_payload(counts))
    mock_groq_client_fn.return_value = mock_groq_client

    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [])

    assert result is not None
    total = sum(len(result[k]) for k in ["technical_questions", "scenario_questions", "problem_solving_questions", "behavioral_questions"])
    assert total == DEFAULT_TOTAL_COUNT
    mock_groq_client.chat.completions.create.assert_called_once()
    assert mock_groq_client.chat.completions.create.call_args.kwargs["model"] == "llama-3.3-70b-versatile"


@patch("app.services.skill_assessment_ai.groq_client")
@patch("app.services.skill_assessment_ai.genai.Client")
def test_generate_quota_error_without_groq_key_still_returns_none(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    """If Groq isn't configured either, behavior must be identical to before
    Groq existed -- None, so the caller falls back to the static bank."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [])

    assert result is None
    mock_groq_client_fn.assert_not_called()


@patch("app.services.skill_assessment_ai.groq_client")
@patch("app.services.skill_assessment_ai.genai.Client")
def test_generate_non_quota_error_never_calls_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    """Groq must only be attempted on a 429 -- a generic failure must return
    None exactly as before, never through Groq."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = RuntimeError("boom")
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_assessment_questions("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", [])

    assert result is None
    mock_groq_client_fn.assert_not_called()


@patch("app.services.skill_assessment_ai.groq_client")
@patch("app.services.skill_assessment_ai.genai.Client")
def test_grade_quota_error_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    items = [{"id": 1, "type": "technical", "question": "q1", "expected_answer_points": "p1", "answer": "a1"}]
    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({
        "results": [{"question_id": 1, "score": 80, "is_correct": True, "explanation": "Solid.", "correct_answer_or_improvement": "N/A"}]
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = grade_assessment_answers(items)

    assert result is not None
    assert result[0]["score"] == 80
    mock_groq_client.chat.completions.create.assert_called_once()


@patch("app.services.skill_assessment_ai.groq_client")
@patch("app.services.skill_assessment_ai.genai.Client")
def test_grade_quota_error_without_groq_key_still_returns_none(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    items = [{"id": 1, "type": "technical", "question": "q1", "expected_answer_points": "p1", "answer": "a1"}]
    result = grade_assessment_answers(items)

    assert result is None
    mock_groq_client_fn.assert_not_called()
