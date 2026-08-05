import json
from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.job_description_ai import parse_job_description_ai


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

VALID_PAYLOAD = {
    "title": "Backend Engineer",
    "required_skills": ["Python", "PostgreSQL", "Docker"],
    "experience_level": "3+ years",
    "qualifications": ["Bachelor's degree in Computer Science"],
    "keywords": ["microservices", "REST", "CI/CD"],
    "cleaned_description": "We are looking for a Backend Engineer with Python and Docker experience.",
}


def test_no_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    assert parse_job_description_ai("some job posting text") is None


def test_ai_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert parse_job_description_ai("some job posting text", ai_enabled=False) is None


def test_empty_text_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert parse_job_description_ai("") is None
    assert parse_job_description_ai("   ") is None


@patch("app.services.job_description_ai.genai.Client")
def test_successful_call_returns_parsed_result(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(VALID_PAYLOAD)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = parse_job_description_ai("We are looking for a Backend Engineer with Python and Docker experience.")
    assert result is not None
    assert result["required_skills"] == ["Python", "PostgreSQL", "Docker"]
    assert result["title"] == "Backend Engineer"
    assert "Backend Engineer" in result["cleaned_description"]


@patch("app.services.job_description_ai.genai.Client")
def test_empty_required_skills_returns_none(mock_client_cls, monkeypatch):
    """Guards against a degenerate AI response silently overriding a genuinely
    better rule-based fallback."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    bad_payload = {**VALID_PAYLOAD, "required_skills": []}
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(bad_payload)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = parse_job_description_ai("some job posting text")
    assert result is None


@patch("app.services.job_description_ai.genai.Client")
def test_api_error_returns_none(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = RuntimeError("boom")
    mock_client_cls.return_value = mock_client

    result = parse_job_description_ai("some job posting text")
    assert result is None


@patch("app.services.job_description_ai.groq_client")
@patch("app.services.job_description_ai.genai.Client")
def test_gemini_quota_error_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response(VALID_PAYLOAD)
    mock_groq_client_fn.return_value = mock_groq_client

    result = parse_job_description_ai("We are looking for a Backend Engineer with Python and Docker experience.")

    assert result is not None
    assert result["required_skills"] == ["Python", "PostgreSQL", "Docker"]
    mock_groq_client.chat.completions.create.assert_called_once()
    assert mock_groq_client.chat.completions.create.call_args.kwargs["model"] == "llama-3.3-70b-versatile"


@patch("app.services.job_description_ai.groq_client")
@patch("app.services.job_description_ai.genai.Client")
def test_gemini_quota_error_without_groq_key_returns_none(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = parse_job_description_ai("some job posting text")

    assert result is None
    mock_groq_client_fn.assert_not_called()


@patch("app.services.job_description_ai.groq_client")
@patch("app.services.job_description_ai.genai.Client")
def test_non_quota_gemini_error_never_calls_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = genai_errors.ClientError(
        400, {"message": "bad request", "status": "INVALID_ARGUMENT"}, None
    )
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = parse_job_description_ai("some job posting text")

    assert result is None
    mock_groq_client_fn.assert_not_called()


def _two_key_client_factory(key1_client, key2_client):
    def factory(api_key, **kwargs):
        return key1_client if api_key == "key-1" else key2_client
    return factory


@patch("app.services.job_description_ai.genai.Client")
def test_second_gemini_key_used_when_first_hits_quota(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = _gemini_quota_error()
    key2_client = Mock()
    key2_client.models.generate_content.return_value = Mock(text=json.dumps(VALID_PAYLOAD))
    mock_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    result = parse_job_description_ai("We are looking for a Backend Engineer with Python and Docker experience.")

    assert result is not None
    assert result["required_skills"] == ["Python", "PostgreSQL", "Docker"]
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()


@patch("app.services.job_description_ai.groq_client")
@patch("app.services.job_description_ai.genai.Client")
def test_both_gemini_keys_exhausted_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = _gemini_quota_error()
    key2_client = Mock()
    key2_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response(VALID_PAYLOAD)
    mock_groq_client_fn.return_value = mock_groq_client

    result = parse_job_description_ai("We are looking for a Backend Engineer with Python and Docker experience.")

    assert result is not None
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()
    mock_groq_client.chat.completions.create.assert_called_once()
