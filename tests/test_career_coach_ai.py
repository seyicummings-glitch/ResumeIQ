import json
from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.career_coach_ai import get_coach_reply

CONVERSATION = [{"role": "user", "content": "Can you explain what a race condition is?"}]
CONTEXT = {"target_role": "Backend Engineer"}


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
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT)
    assert result["source"] == "fallback"
    assert "isn't available" in result["reply"]


def test_ai_disabled_returns_fallback_even_with_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT, ai_enabled=False)
    assert result["source"] == "fallback"


def test_empty_conversation_still_returns_fallback_gracefully(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = get_coach_reply(conversation=[])
    assert result["source"] == "fallback"


def test_missing_context_does_not_crash(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = get_coach_reply(conversation=CONVERSATION, context=None)
    assert result["source"] == "fallback"


@patch("app.services.career_coach_ai.genai.Client")
def test_successful_call_returns_ai_reply(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({"reply": "A race condition happens when two operations access shared state without proper ordering."})
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT)
    assert result["source"] == "ai"
    assert "race condition" in result["reply"]


@patch("app.services.career_coach_ai.genai.Client")
def test_full_context_is_included_in_system_prompt(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({"reply": "Sure, let's dig into Redis locking."})
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    context = {
        "target_role": "Backend Engineer",
        "industry": "Fintech",
        "resume_text": "Built APIs with FastAPI and Redis.",
        "resume_skills": ["Python", "FastAPI"],
        "jd_title": "Senior Backend Engineer",
        "jd_content": "Looking for someone strong in distributed systems.",
        "missing_skills": ["Kubernetes"],
        "roadmap_summary": "- Foundation: Git, Clean code",
        "skill_assessment_summary": "Technical score: 70/100.",
        "interview_summary": "Areas to improve: give more specific examples.",
    }
    get_coach_reply(
        conversation=CONVERSATION,
        context=context,
        topic_context="Title: Distributed locking with Redis\nWhy it matters: prevents race conditions.",
    )
    sent_config = mock_client_cls.return_value.models.generate_content.call_args.kwargs["config"]
    prompt = sent_config.system_instruction
    assert "Backend Engineer" in prompt
    assert "Fintech" in prompt
    assert "FastAPI" in prompt
    assert "Senior Backend Engineer" in prompt
    assert "Kubernetes" in prompt
    assert "Git, Clean code" in prompt
    assert "70/100" in prompt
    assert "specific examples" in prompt
    assert "Distributed locking with Redis" in prompt


@patch("app.services.career_coach_ai.genai.Client")
def test_rate_limit_error_returns_fallback(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ClientError(
        429, {"message": "rate limited", "status": "RESOURCE_EXHAUSTED"}, None
    )
    mock_client_cls.return_value = mock_client

    result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT)
    assert result["source"] == "fallback"


@patch("app.services.career_coach_ai.genai.Client")
def test_non_quota_error_returns_fallback_without_trying_groq(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ClientError(
        400, {"message": "bad request", "status": "INVALID_ARGUMENT"}, None
    )
    mock_client_cls.return_value = mock_client

    with patch("app.services.career_coach_ai.groq_client") as mock_groq_client_fn:
        result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT)
        assert result["source"] == "fallback"
        mock_groq_client_fn.assert_not_called()


@patch("app.services.career_coach_ai.groq_client")
@patch("app.services.career_coach_ai.genai.Client")
def test_gemini_quota_error_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({"reply": "From Groq."})
    mock_groq_client_fn.return_value = mock_groq_client

    result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT)

    assert result["source"] == "ai"
    assert result["reply"] == "From Groq."
    mock_groq_client.chat.completions.create.assert_called_once()
    assert mock_groq_client.chat.completions.create.call_args.kwargs["model"] == "llama-3.3-70b-versatile"


@patch("app.services.career_coach_ai.groq_client")
@patch("app.services.career_coach_ai.genai.Client")
def test_gemini_quota_error_without_groq_key_still_falls_back_normally(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT)

    assert result["source"] == "fallback"
    mock_groq_client_fn.assert_not_called()


def _two_key_client_factory(key1_client, key2_client):
    def factory(api_key, **kwargs):
        return key1_client if api_key == "key-1" else key2_client
    return factory


@patch("app.services.career_coach_ai.genai.Client")
def test_second_gemini_key_used_when_first_hits_quota(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = _gemini_quota_error()
    key2_client = Mock()
    key2_client.models.generate_content.return_value = Mock(text=json.dumps({"reply": "From the second key."}))
    mock_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT)

    assert result["source"] == "ai"
    assert result["reply"] == "From the second key."
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()


@patch("app.services.career_coach_ai.groq_client")
@patch("app.services.career_coach_ai.genai.Client")
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
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({"reply": "From Groq."})
    mock_groq_client_fn.return_value = mock_groq_client

    result = get_coach_reply(conversation=CONVERSATION, context=CONTEXT)

    assert result["source"] == "ai"
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()
    mock_groq_client.chat.completions.create.assert_called_once()
