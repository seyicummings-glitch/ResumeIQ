import json
from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.learning_roadmap_ai import STAGE_NAMES, TOPICS_PER_STAGE, generate_learning_roadmap


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


def _topic(i):
    return {
        "title": f"Topic {i}",
        "why_it_matters": "It matters.",
        "learning_objectives": ["Objective A", "Objective B"],
        "resources": [
            {"name": "Resource A", "type": "Course", "provider": "Udemy"},
            {"name": "Resource B", "type": "Free", "provider": "Docs"},
        ],
        "projects": ["Project A"],
        "exercises": ["Exercise A"],
        "estimated_hours": 10,
        "priority": "high",
    }


def _stage(name):
    return {
        "stage": name,
        "description": f"{name} description",
        "estimated_duration": "2-3 weeks",
        "milestone": f"{name} milestone",
        "topics": [_topic(i) for i in range(TOPICS_PER_STAGE)],
    }


VALID_PAYLOAD = {"stages": [_stage(name) for name in STAGE_NAMES]}


def test_no_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd")
    assert result is None


def test_ai_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd", ai_enabled=False)
    assert result is None


@patch("app.services.learning_roadmap_ai.genai.Client")
def test_successful_call_returns_four_stages(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(VALID_PAYLOAD)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd")
    assert result is not None
    assert [s["stage"] for s in result["stages"]] == STAGE_NAMES
    assert len(result["stages"][0]["topics"]) == TOPICS_PER_STAGE


@patch("app.services.learning_roadmap_ai.genai.Client")
def test_wrong_stage_count_returns_none(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    bad_payload = {"stages": [_stage(name) for name in STAGE_NAMES[:3]]}
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(bad_payload)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd")
    assert result is None


@patch("app.services.learning_roadmap_ai.genai.Client")
def test_wrong_stage_order_returns_none(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    shuffled = ["Intermediate", "Foundation", "Job Ready", "Advanced"]
    bad_payload = {"stages": [_stage(name) for name in shuffled]}
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(bad_payload)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd")
    assert result is None


@patch("app.services.learning_roadmap_ai.genai.Client")
def test_api_error_returns_none(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = RuntimeError("boom")
    mock_client_cls.return_value = mock_client

    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd")
    assert result is None


@patch("app.services.learning_roadmap_ai.genai.Client")
def test_target_role_is_included_in_prompt(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(VALID_PAYLOAD)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    generate_learning_roadmap("Full Stack Developer", "Fintech", "mid", "resume with no react mentioned", ["Python"], [], "jd")
    sent_contents = mock_client_cls.return_value.models.generate_content.call_args.kwargs["contents"]
    assert "Full Stack Developer" in sent_contents
    assert "Fintech" in sent_contents


@patch("app.services.learning_roadmap_ai.groq_client")
@patch("app.services.learning_roadmap_ai.genai.Client")
def test_gemini_quota_error_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response(VALID_PAYLOAD)
    mock_groq_client_fn.return_value = mock_groq_client

    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd")

    assert result is not None
    assert [s["stage"] for s in result["stages"]] == STAGE_NAMES
    mock_groq_client.chat.completions.create.assert_called_once()
    assert mock_groq_client.chat.completions.create.call_args.kwargs["model"] == "llama-3.3-70b-versatile"


@patch("app.services.learning_roadmap_ai.groq_client")
@patch("app.services.learning_roadmap_ai.genai.Client")
def test_gemini_quota_error_without_groq_key_returns_none(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd")

    assert result is None
    mock_groq_client_fn.assert_not_called()


@patch("app.services.learning_roadmap_ai.groq_client")
@patch("app.services.learning_roadmap_ai.genai.Client")
def test_non_quota_gemini_error_never_calls_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = genai_errors.ClientError(
        400, {"message": "bad request", "status": "INVALID_ARGUMENT"}, None
    )
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_learning_roadmap("Backend Engineer", "Tech", "mid", "resume", ["Python"], ["Docker"], "jd")

    assert result is None
    mock_groq_client_fn.assert_not_called()
