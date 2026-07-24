import json
from unittest.mock import patch, Mock
import anthropic
from app.services.ai_suggestions import generate_resume_suggestions


def test_no_api_key_returns_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = generate_resume_suggestions("some resume text", None, {"ats_issues": ["No email address detected."]})
    assert result["source"] == "fallback"
    assert any(s["category"] == "ATS Compatibility" for s in result["suggestions"])


@patch("app.services.ai_suggestions.anthropic.Anthropic")
def test_successful_call_returns_ai_suggestions(mock_anthropic_cls, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = Mock()
    mock_block = Mock()
    mock_block.type = "text"
    mock_block.text = json.dumps({
        "overall_assessment": "Solid resume overall.",
        "suggestions": [
            {"category": "Skills", "issue": "No cloud skills listed", "suggestion": "Add AWS or Azure experience if applicable."}
        ]
    })
    mock_response = Mock()
    mock_response.content = [mock_block]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic_cls.return_value = mock_client

    result = generate_resume_suggestions("resume text", None, {})
    assert result["source"] == "ai"
    assert result["overall_assessment"] == "Solid resume overall."
    assert len(result["suggestions"]) == 1


@patch("app.services.ai_suggestions.anthropic.Anthropic")
def test_rate_limit_error_returns_fallback(mock_anthropic_cls, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = Mock()
    mock_client.messages.create.side_effect = anthropic.RateLimitError(
        message="rate limited", response=Mock(headers={}), body=None
    )
    mock_anthropic_cls.return_value = mock_client

    result = generate_resume_suggestions("resume text", None, {"ats_issues": []})
    assert result["source"] == "fallback"
    assert "rate-limited" in result["overall_assessment"]


@patch("app.services.ai_suggestions.anthropic.Anthropic")
def test_connection_error_returns_fallback(mock_anthropic_cls, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = Mock()
    mock_client.messages.create.side_effect = anthropic.APIConnectionError(request=Mock())
    mock_anthropic_cls.return_value = mock_client

    result = generate_resume_suggestions("resume text", None, {"ats_issues": []})
    assert result["source"] == "fallback"
