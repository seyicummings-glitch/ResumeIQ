import json
from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.ai_interviewer import get_interviewer_reply


def test_no_api_key_starts_with_first_fallback_question(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = get_interviewer_reply(
        resume_text="Built APIs in Python for 5 years.",
        jd_content="Looking for a backend engineer with Docker and Kubernetes experience.",
        jd_title="Backend Engineer",
        missing_skills=["docker", "kubernetes"],
        resume_skills=["python"],
        conversation=[],
    )
    assert result["source"] == "fallback"
    assert result["done"] is False
    assert result["feedback"] == ""
    assert result["question"]


def test_no_api_key_advances_through_questions(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    conversation = [
        {"role": "interviewer", "content": "first question"},
        {"role": "candidate", "content": "my answer"},
    ]
    result = get_interviewer_reply(
        resume_text="Built APIs in Python for 5 years.",
        jd_content="Looking for a backend engineer with Docker experience.",
        jd_title="Backend Engineer",
        missing_skills=["docker"],
        resume_skills=["python"],
        conversation=conversation,
    )
    assert result["source"] == "fallback"
    assert result["feedback"]
    assert result["question"]


def test_no_api_key_no_context_still_falls_back_to_universal_questions(monkeypatch):
    """Even with no resume/JD context, build_interview_questions always
    returns the universal behavioral/system-design/role questions, so the
    fallback interview can still proceed rather than dead-ending."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = get_interviewer_reply(
        resume_text="",
        jd_content="",
        jd_title="",
        missing_skills=[],
        resume_skills=[],
        conversation=[],
    )
    assert result["source"] == "fallback"
    assert result["done"] is False
    assert result["question"]


def test_ai_disabled_returns_fallback_even_with_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = get_interviewer_reply(
        resume_text="Built APIs in Python for 5 years.",
        jd_content="Looking for a backend engineer with Docker experience.",
        jd_title="Backend Engineer",
        missing_skills=["docker"],
        resume_skills=["python"],
        conversation=[],
        ai_enabled=False,
    )
    assert result["source"] == "fallback"


def _mock_json_response(mock_client_cls, payload):
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps(payload)
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client
    return mock_client


@patch("app.services.ai_interviewer.genai.Client")
def test_successful_call_returns_ai_reply(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _mock_json_response(mock_client_cls, {
        "feedback": "",
        "question": "Tell me about a recent project.",
    })

    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=[],
        resume_skills=[],
        conversation=[],
    )
    assert result["source"] == "ai"
    assert result["feedback"] == ""
    assert "project" in result["question"]
    assert result["done"] is False


@patch("app.services.ai_interviewer.genai.Client")
def test_successful_call_with_prior_answer_returns_feedback(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _mock_json_response(mock_client_cls, {
        "feedback": "You explained the architecture but didn't mention any metrics or scale.",
        "question": "How would you handle a 10x increase in traffic to that service?",
    })

    conversation = [
        {"role": "interviewer", "content": "Tell me about a recent project."},
        {"role": "candidate", "content": "I built a REST API for a fintech startup."},
    ]
    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=[],
        resume_skills=[],
        conversation=conversation,
    )
    assert result["source"] == "ai"
    assert "metrics" in result["feedback"]
    assert "10x" in result["question"]


@patch("app.services.ai_interviewer.genai.Client")
def test_preferred_language_is_passed_into_the_system_prompt(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _mock_json_response(mock_client_cls, {
        "feedback": "",
        "question": "Cuéntame sobre un proyecto reciente.",
    })

    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=[],
        resume_skills=[],
        conversation=[],
        preferred_language="es-ES",
    )

    assert result["source"] == "ai"
    sent_config = mock_client_cls.return_value.models.generate_content.call_args.kwargs["config"]
    assert "es-ES" in sent_config.system_instruction


@patch("app.services.ai_interviewer.genai.Client")
def test_no_preferred_language_defaults_system_prompt_to_english_opening(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _mock_json_response(mock_client_cls, {
        "feedback": "",
        "question": "Tell me about a recent project.",
    })

    get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=[],
        resume_skills=[],
        conversation=[],
    )

    sent_config = mock_client_cls.return_value.models.generate_content.call_args.kwargs["config"]
    assert "Default to English" in sent_config.system_instruction


@patch("app.services.ai_interviewer.genai.Client")
def test_conversation_is_passed_as_role_tagged_contents(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _mock_json_response(mock_client_cls, {
        "feedback": "Good structure.",
        "question": "What would you do differently?",
    })

    conversation = [
        {"role": "interviewer", "content": "Tell me about a recent project."},
        {"role": "candidate", "content": "I built a REST API."},
    ]
    get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=[],
        resume_skills=[],
        conversation=conversation,
    )

    sent_contents = mock_client_cls.return_value.models.generate_content.call_args.kwargs["contents"]
    assert sent_contents == [
        {"role": "model", "parts": [{"text": "Tell me about a recent project."}]},
        {"role": "user", "parts": [{"text": "I built a REST API."}]},
    ]


@patch("app.services.ai_interviewer.genai.Client")
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

    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=["docker"],
        resume_skills=["python"],
        conversation=[],
    )
    assert result["source"] == "fallback"


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


@patch("app.services.ai_interviewer.groq_client")
@patch("app.services.ai_interviewer.genai.Client")
def test_gemini_quota_error_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({
        "feedback": "",
        "question": "Tell me about a recent project.",
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=["docker"],
        resume_skills=["python"],
        conversation=[],
    )

    assert result["source"] == "ai"
    assert "project" in result["question"]
    mock_groq_client.chat.completions.create.assert_called_once()
    assert mock_groq_client.chat.completions.create.call_args.kwargs["model"] == "llama-3.3-70b-versatile"


@patch("app.services.ai_interviewer.groq_client")
@patch("app.services.ai_interviewer.genai.Client")
def test_gemini_quota_error_without_groq_key_still_falls_back_normally(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    """If Groq isn't configured either, behavior must be identical to before
    Groq existed -- the rule-based fallback, not an error."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=["docker"],
        resume_skills=["python"],
        conversation=[],
    )

    assert result["source"] == "fallback"
    mock_groq_client_fn.assert_not_called()


@patch("app.services.ai_interviewer.groq_client")
@patch("app.services.ai_interviewer.genai.Client")
def test_gemini_server_error_never_calls_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    """Groq must only be attempted on a 429 -- a ServerError must fail over to
    the rule-based fallback exactly as before, never through Groq."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = genai_errors.ServerError(
        503, {"message": "unavailable", "status": "UNAVAILABLE"}, None
    )
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=["docker"],
        resume_skills=["python"],
        conversation=[],
    )

    assert result["source"] == "fallback"
    mock_groq_client_fn.assert_not_called()


def _two_key_client_factory(key1_client, key2_client):
    def factory(api_key, **kwargs):
        return key1_client if api_key == "key-1" else key2_client
    return factory


@patch("app.services.ai_interviewer.genai.Client")
def test_second_gemini_key_used_when_first_hits_quota(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = _gemini_quota_error()
    key2_client = Mock()
    key2_response = Mock()
    key2_response.text = json.dumps({"feedback": "", "question": "From the second key."})
    key2_client.models.generate_content.return_value = key2_response
    mock_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=["docker"],
        resume_skills=["python"],
        conversation=[],
    )

    assert result["source"] == "ai"
    assert result["question"] == "From the second key."
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()


@patch("app.services.ai_interviewer.groq_client")
@patch("app.services.ai_interviewer.genai.Client")
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
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({
        "feedback": "", "question": "From Groq.",
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = get_interviewer_reply(
        resume_text="resume text",
        jd_content="jd text",
        jd_title="Backend Engineer",
        missing_skills=["docker"],
        resume_skills=["python"],
        conversation=[],
    )

    assert result["source"] == "ai"
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()
    mock_groq_client.chat.completions.create.assert_called_once()
