import json
from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.interview_feedback import generate_interview_feedback

TRANSCRIPT = [
    {"role": "interviewer", "content": "Tell me about a recent project."},
    {"role": "candidate", "content": "I built a REST API for a fintech startup using Python."},
]


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
    result = generate_interview_feedback(
        transcript=TRANSCRIPT,
        resume_text="resume text",
        jd_title="Backend Engineer",
        jd_content="jd text",
        missing_skills=["kubernetes"],
    )
    assert result["source"] == "fallback"
    assert "1 question" in result["overall_assessment"]
    assert result["study_topics"] == ["kubernetes"]


def test_no_api_key_no_missing_skills_still_returns_study_topics(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = generate_interview_feedback(
        transcript=[],
        resume_text="",
        jd_title="",
        jd_content="",
        missing_skills=[],
    )
    assert result["source"] == "fallback"
    assert result["study_topics"]
    assert isinstance(result["strengths"], list)
    assert isinstance(result["areas_to_improve"], list)


def test_ai_disabled_returns_fallback_even_with_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = generate_interview_feedback(
        transcript=TRANSCRIPT,
        resume_text="resume text",
        jd_title="Backend Engineer",
        jd_content="jd text",
        missing_skills=[],
        ai_enabled=False,
    )
    assert result["source"] == "fallback"
    assert "disabled by the administrator" in result["overall_assessment"]


@patch("app.services.interview_feedback.genai.Client")
def test_successful_call_returns_ai_feedback(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "overall_assessment": "Solid technical depth, but answers lacked concrete metrics.",
        "strengths": ["Clear explanation of the API architecture."],
        "areas_to_improve": ["Quantify impact with numbers."],
        "study_topics": ["Kubernetes", "System design basics"],
        "role_knowledge_tips": ["Fintech interviews often probe on data consistency."],
    })
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_interview_feedback(
        transcript=TRANSCRIPT,
        resume_text="resume text",
        jd_title="Backend Engineer",
        jd_content="jd text",
        missing_skills=["kubernetes"],
    )
    assert result["source"] == "ai"
    assert "metrics" in result["overall_assessment"]
    assert result["study_topics"] == ["Kubernetes", "System design basics"]


@patch("app.services.interview_feedback.genai.Client")
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

    result = generate_interview_feedback(
        transcript=TRANSCRIPT,
        resume_text="resume text",
        jd_title="Backend Engineer",
        jd_content="jd text",
        missing_skills=[],
    )
    assert result["source"] == "fallback"
    assert "rate-limited" in result["overall_assessment"]


@patch("app.services.interview_feedback.groq_client")
@patch("app.services.interview_feedback.genai.Client")
def test_gemini_quota_error_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({
        "overall_assessment": "Solid technical depth, but answers lacked concrete metrics.",
        "strengths": ["Clear explanation of the API architecture."],
        "areas_to_improve": ["Quantify impact with numbers."],
        "study_topics": ["Kubernetes", "System design basics"],
        "role_knowledge_tips": ["Fintech interviews often probe on data consistency."],
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = generate_interview_feedback(
        transcript=TRANSCRIPT,
        resume_text="resume text",
        jd_title="Backend Engineer",
        jd_content="jd text",
        missing_skills=["kubernetes"],
    )

    assert result["source"] == "ai"
    assert "metrics" in result["overall_assessment"]
    mock_groq_client.chat.completions.create.assert_called_once()
    assert mock_groq_client.chat.completions.create.call_args.kwargs["model"] == "llama-3.3-70b-versatile"


@patch("app.services.interview_feedback.groq_client")
@patch("app.services.interview_feedback.genai.Client")
def test_gemini_quota_error_without_groq_key_still_falls_back_normally(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_interview_feedback(
        transcript=TRANSCRIPT,
        resume_text="resume text",
        jd_title="Backend Engineer",
        jd_content="jd text",
        missing_skills=[],
    )

    assert result["source"] == "fallback"
    mock_groq_client_fn.assert_not_called()


@patch("app.services.interview_feedback.genai.Client")
def test_server_error_returns_fallback(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ServerError(
        503, {"message": "unavailable", "status": "UNAVAILABLE"}, None
    )
    mock_client_cls.return_value = mock_client

    result = generate_interview_feedback(
        transcript=TRANSCRIPT,
        resume_text="resume text",
        jd_title="Backend Engineer",
        jd_content="jd text",
        missing_skills=[],
    )
    assert result["source"] == "fallback"
    assert "Could not reach the AI service" in result["overall_assessment"]


def _two_key_client_factory(key1_client, key2_client):
    def factory(api_key, **kwargs):
        return key1_client if api_key == "key-1" else key2_client
    return factory


@patch("app.services.interview_feedback.genai.Client")
def test_second_gemini_key_used_when_first_hits_quota(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = _gemini_quota_error()
    key2_client = Mock()
    key2_client.models.generate_content.return_value = Mock(text=json.dumps({
        "overall_assessment": "From the second key.",
        "strengths": [], "areas_to_improve": [], "study_topics": [], "role_knowledge_tips": [],
    }))
    mock_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    result = generate_interview_feedback(
        transcript=TRANSCRIPT, resume_text="resume text", jd_title="Backend Engineer",
        jd_content="jd text", missing_skills=[],
    )

    assert result["source"] == "ai"
    assert result["overall_assessment"] == "From the second key."
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()


@patch("app.services.interview_feedback.groq_client")
@patch("app.services.interview_feedback.genai.Client")
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
        "overall_assessment": "From Groq.",
        "strengths": [], "areas_to_improve": [], "study_topics": [], "role_knowledge_tips": [],
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = generate_interview_feedback(
        transcript=TRANSCRIPT, resume_text="resume text", jd_title="Backend Engineer",
        jd_content="jd text", missing_skills=[],
    )

    assert result["source"] == "ai"
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()
    mock_groq_client.chat.completions.create.assert_called_once()
