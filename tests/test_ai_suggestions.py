import json
from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.ai_suggestions import generate_resume_suggestions


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


def test_no_api_key_returns_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = generate_resume_suggestions("some resume text", None, {"ats_issues": ["No email address detected."]})
    assert result["source"] == "fallback"
    assert any(s["category"] == "ATS Compatibility" for s in result["suggestions"])


def test_ai_disabled_returns_fallback_even_with_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = generate_resume_suggestions("some resume text", None, {}, ai_enabled=False)
    assert result["source"] == "fallback"
    assert "disabled by the administrator" in result["overall_assessment"]


@patch("app.services.ai_suggestions.genai.Client")
def test_successful_call_returns_ai_suggestions(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "overall_assessment": "Solid resume overall.",
        "suggestions": [
            {"category": "Skills", "issue": "No cloud skills listed", "suggestion": "Add AWS or Azure experience if applicable."}
        ]
    })
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_resume_suggestions("resume text", None, {})
    assert result["source"] == "ai"
    assert result["overall_assessment"] == "Solid resume overall."
    assert len(result["suggestions"]) == 1


@patch("app.services.ai_suggestions.genai.Client")
def test_rate_limit_error_returns_fallback(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    # Must not depend on whatever GROQ_API_KEY happens to be in the real .env —
    # this test is specifically about behavior when Groq isn't available.
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ClientError(
        429, {"message": "rate limited", "status": "RESOURCE_EXHAUSTED"}, None
    )
    mock_client_cls.return_value = mock_client

    result = generate_resume_suggestions("resume text", None, {"ats_issues": []})
    assert result["source"] == "fallback"
    assert "rate-limited" in result["overall_assessment"]


@patch("app.services.ai_suggestions.groq_client")
@patch("app.services.ai_suggestions.genai.Client")
def test_gemini_quota_error_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({
        "overall_assessment": "Solid resume overall.",
        "suggestions": [{"category": "Skills", "issue": "No cloud skills listed", "suggestion": "Add AWS if applicable."}],
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = generate_resume_suggestions("resume text", None, {})

    assert result["source"] == "ai"
    assert result["overall_assessment"] == "Solid resume overall."
    mock_groq_client.chat.completions.create.assert_called_once()
    assert mock_groq_client.chat.completions.create.call_args.kwargs["model"] == "llama-3.3-70b-versatile"


@patch("app.services.ai_suggestions.groq_client")
@patch("app.services.ai_suggestions.genai.Client")
def test_gemini_quota_error_without_groq_key_still_falls_back_normally(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_resume_suggestions("resume text", None, {"ats_issues": []})

    assert result["source"] == "fallback"
    assert "rate-limited" in result["overall_assessment"]
    mock_groq_client_fn.assert_not_called()


@patch("app.services.ai_suggestions.groq_client")
@patch("app.services.ai_suggestions.genai.Client")
def test_non_quota_gemini_error_never_calls_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = genai_errors.ClientError(
        400, {"message": "bad request", "status": "INVALID_ARGUMENT"}, None
    )
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_resume_suggestions("resume text", None, {"ats_issues": []})

    assert result["source"] == "fallback"
    mock_groq_client_fn.assert_not_called()


@patch("app.services.ai_suggestions.genai.Client")
def test_server_error_returns_fallback(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ServerError(
        503, {"message": "unavailable", "status": "UNAVAILABLE"}, None
    )
    mock_client_cls.return_value = mock_client

    result = generate_resume_suggestions("resume text", None, {"ats_issues": []})
    assert result["source"] == "fallback"
    assert "Could not reach the AI service" in result["overall_assessment"]
