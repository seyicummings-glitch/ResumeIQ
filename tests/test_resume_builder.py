import json
from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.resume_builder import generate_enhanced_resume, chat_about_resume


def _gemini_quota_exhausted_error():
    """Mirrors the real error body Gemini returns when the daily free-tier quota
    is exhausted (as opposed to a generic short-term rate limit)."""
    return genai_errors.ClientError(
        429,
        {
            "error": {
                "code": 429,
                "message": "You exceeded your current quota, please check your plan and billing details.",
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}
                        ],
                    }
                ],
            }
        },
        None,
    )


def _mock_groq_response(payload: dict) -> Mock:
    response = Mock()
    response.choices = [Mock(message=Mock(content=json.dumps(payload)))]
    return response


def _two_key_client_factory(key1_client, key2_client):
    """genai.Client(api_key=..., http_options=...) is called positionally by
    keyword in this codebase -- routes the mock to whichever client belongs to
    the key actually passed in, so each key's mocked behavior stays distinct."""
    def factory(api_key, **kwargs):
        return key1_client if api_key == "key-1" else key2_client
    return factory


def test_no_api_key_returns_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = generate_enhanced_resume(
        "some resume text",
        ["Kubernetes"],
        {
            "original_summary": "Experienced backend engineer.",
            "original_experience": "Built APIs at Acme Corp.",
            "original_skills": ["Python", "SQL"],
        },
    )
    assert result["source"] == "fallback"
    assert result["summary"] == "Experienced backend engineer."
    assert "Python" in result["skills_section"]
    assert "overall_assessment" in result


def test_no_api_key_returns_fallback_with_empty_data(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = generate_enhanced_resume("some resume text", [], {})
    assert result["source"] == "fallback"
    assert result["summary"]
    assert isinstance(result["experience_bullets"], list)
    assert result["skills_section"]


def test_ai_disabled_returns_fallback_even_with_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = generate_enhanced_resume("some resume text", [], {}, ai_enabled=False)
    assert result["source"] == "fallback"
    assert "disabled by the administrator" in result["overall_assessment"]


@patch("app.services.resume_builder.genai.Client")
def test_successful_call_returns_ai_result(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "summary": "Results-driven backend engineer with 5 years of experience.",
        "experience_bullets": ["Built and scaled REST APIs serving 1M+ requests/day."],
        "skills_section": "Languages: Python, SQL",
    })
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = generate_enhanced_resume("resume text", [], {})
    assert result["source"] == "ai"
    assert "backend engineer" in result["summary"]


@patch("app.services.resume_builder.genai.Client")
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

    result = generate_enhanced_resume("resume text", [], {})
    assert result["source"] == "fallback"
    assert "rate-limited" in result["overall_assessment"]


@patch("app.services.resume_builder.genai.Client")
def test_server_error_returns_fallback(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ServerError(
        503, {"message": "unavailable", "status": "UNAVAILABLE"}, None
    )
    mock_client_cls.return_value = mock_client

    result = generate_enhanced_resume("resume text", [], {})
    assert result["source"] == "fallback"
    assert "Could not reach the AI service" in result["overall_assessment"]


@patch("app.services.resume_builder.genai.Client")
def test_other_client_error_returns_fallback(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ClientError(
        400, {"message": "bad request", "status": "INVALID_ARGUMENT"}, None
    )
    mock_client_cls.return_value = mock_client

    result = generate_enhanced_resume("resume text", [], {})
    assert result["source"] == "fallback"
    assert "The AI service returned an error" in result["overall_assessment"]


@patch("app.services.resume_builder.genai.Client")
def test_chat_builds_from_scratch_with_no_resume_or_draft(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "reply": "Got it — I've drafted a summary based on what you told me.",
        "summary": "Backend engineer with 3 years of Python experience.",
        "experience_bullets": ["Built REST APIs at a fintech startup."],
        "skills_section": "Python, PostgreSQL",
    })
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = chat_about_resume(
        conversation=[{"role": "user", "content": "I'm a backend engineer with 3 years of Python experience at a fintech startup, build me a resume."}],
        resume_text="",
        missing_skills=[],
        current_summary="",
        current_experience_bullets=[],
        current_skills_section="",
    )
    assert result["source"] == "ai"
    assert result["summary"]
    assert result["experience_bullets"]


def test_chat_no_api_key_returns_draft_unchanged(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = chat_about_resume(
        conversation=[{"role": "user", "content": "Remove the second bullet."}],
        resume_text="resume text",
        missing_skills=[],
        current_summary="Current summary.",
        current_experience_bullets=["Bullet one.", "Bullet two."],
        current_skills_section="Python, SQL",
    )
    assert result["source"] == "fallback"
    assert result["summary"] == "Current summary."
    assert result["experience_bullets"] == ["Bullet one.", "Bullet two."]
    assert result["skills_section"] == "Python, SQL"


def test_chat_ai_disabled_returns_draft_unchanged(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = chat_about_resume(
        conversation=[{"role": "user", "content": "Remove the second bullet."}],
        resume_text="resume text",
        missing_skills=[],
        current_summary="Current summary.",
        current_experience_bullets=["Bullet one.", "Bullet two."],
        current_skills_section="Python, SQL",
        ai_enabled=False,
    )
    assert result["source"] == "fallback"
    assert "disabled by the administrator" in result["reply"]
    assert result["experience_bullets"] == ["Bullet one.", "Bullet two."]


@patch("app.services.resume_builder.genai.Client")
def test_chat_successful_call_returns_updated_draft(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "reply": "Done — removed the second bullet.",
        "summary": "Current summary.",
        "experience_bullets": ["Bullet one."],
        "skills_section": "Python, SQL",
    })
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = chat_about_resume(
        conversation=[{"role": "user", "content": "Remove the second bullet."}],
        resume_text="resume text",
        missing_skills=[],
        current_summary="Current summary.",
        current_experience_bullets=["Bullet one.", "Bullet two."],
        current_skills_section="Python, SQL",
    )
    assert result["source"] == "ai"
    assert result["experience_bullets"] == ["Bullet one."]
    assert "removed" in result["reply"]


@patch("app.services.resume_builder.genai.Client")
def test_chat_jd_content_included_in_system_prompt(mock_client_cls, monkeypatch):
    """A job description extracted from a URL the user pasted (the AI itself
    can't browse links) must actually ground the AI's tailoring, not just sit
    unused in the request."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "reply": "Tailored your resume toward this role.",
        "summary": "Backend engineer.",
        "experience_bullets": [],
        "skills_section": "Python",
    })
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    chat_about_resume(
        conversation=[{"role": "user", "content": "Tailor my resume to this job."}],
        resume_text="resume text",
        missing_skills=[],
        current_summary="",
        current_experience_bullets=[],
        current_skills_section="",
        jd_content="We need a Backend Engineer skilled in Python, FastAPI, and PostgreSQL.",
    )

    sent_config = mock_client_cls.return_value.models.generate_content.call_args.kwargs["config"]
    assert "FastAPI" in sent_config.system_instruction
    assert "PostgreSQL" in sent_config.system_instruction


@patch("app.services.resume_builder.genai.Client")
def test_chat_error_leaves_draft_unchanged(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    # Must not depend on whatever GROQ_API_KEY happens to be in the real .env —
    # this test is specifically about behavior when Groq isn't available.
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ClientError(
        429, {"message": "rate limited", "status": "RESOURCE_EXHAUSTED"}, None
    )
    mock_client_cls.return_value = mock_client

    result = chat_about_resume(
        conversation=[{"role": "user", "content": "Remove the second bullet."}],
        resume_text="resume text",
        missing_skills=[],
        current_summary="Current summary.",
        current_experience_bullets=["Bullet one.", "Bullet two."],
        current_skills_section="Python, SQL",
    )
    assert result["source"] == "fallback"
    assert result["experience_bullets"] == ["Bullet one.", "Bullet two."]
    assert "fast" in result["reply"]


# --- Groq fallback -------------------------------------------------------


@patch("app.services.resume_builder.groq_client")
@patch("app.services.resume_builder.genai.Client")
def test_gemini_quota_error_falls_back_to_groq_for_generate(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_exhausted_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({
        "summary": "Backend engineer with proven API experience.",
        "experience_bullets": ["Built scalable REST APIs serving high traffic."],
        "skills_section": "Languages: Python, SQL",
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = generate_enhanced_resume("resume text", ["Kubernetes"], {"original_skills": ["Python"]})

    assert result["source"] == "ai"
    assert "Backend engineer" in result["summary"]
    assert result["experience_bullets"] == ["Built scalable REST APIs serving high traffic."]

    mock_groq_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_groq_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "llama-3.3-70b-versatile"
    assert call_kwargs["response_format"] == {"type": "json_object"}

    mock_groq_client_fn.assert_called_once_with("groq-test-key")


@patch("app.services.resume_builder.groq_client")
@patch("app.services.resume_builder.genai.Client")
def test_gemini_quota_error_falls_back_to_groq_for_chat(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_exhausted_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({
        "reply": "Done — removed the second bullet.",
        "summary": "Current summary.",
        "experience_bullets": ["Bullet one."],
        "skills_section": "Python, SQL",
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = chat_about_resume(
        conversation=[{"role": "user", "content": "Remove the second bullet."}],
        resume_text="resume text",
        missing_skills=[],
        current_summary="Current summary.",
        current_experience_bullets=["Bullet one.", "Bullet two."],
        current_skills_section="Python, SQL",
    )

    assert result["source"] == "ai"
    assert result["experience_bullets"] == ["Bullet one."]
    assert "removed" in result["reply"]
    mock_groq_client.chat.completions.create.assert_called_once()


@patch("app.services.resume_builder.groq_client")
@patch("app.services.resume_builder.genai.Client")
def test_gemini_quota_error_without_groq_key_still_falls_back_normally(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    """If Groq isn't configured either, behavior must be identical to before Groq
    existed -- the deterministic fallback, not an error."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_exhausted_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_enhanced_resume("resume text", [], {"original_skills": ["Python"]})

    assert result["source"] == "fallback"
    assert "daily usage limit" in result["overall_assessment"]
    mock_groq_client_fn.assert_not_called()


@patch("app.services.resume_builder.groq_client")
@patch("app.services.resume_builder.genai.Client")
def test_non_quota_gemini_error_never_calls_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    """Groq must only be attempted on a 429 -- any other Gemini failure (a real
    bug, bad request, server error) must fail over to the existing fallback
    exactly as before, never through Groq."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = genai_errors.ClientError(
        400, {"message": "bad request", "status": "INVALID_ARGUMENT"}, None
    )
    mock_gemini_client_cls.return_value = mock_gemini_client

    result = generate_enhanced_resume("resume text", [], {})

    assert result["source"] == "fallback"
    mock_groq_client_fn.assert_not_called()


@patch("app.services.resume_builder.groq_client")
@patch("app.services.resume_builder.genai.Client")
def test_groq_also_failing_falls_back_normally(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    """If both providers fail, the user still gets the deterministic fallback,
    never a raw error."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = _gemini_quota_exhausted_error()
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.side_effect = RuntimeError("Groq is down")
    mock_groq_client_fn.return_value = mock_groq_client

    result = generate_enhanced_resume("resume text", [], {"original_skills": ["Python"]})

    assert result["source"] == "fallback"
    assert "daily usage limit" in result["overall_assessment"]


# --- Second Gemini key cascade ---------------------------------------------


@patch("app.services.resume_builder.genai.Client")
def test_second_gemini_key_used_when_first_hits_quota_for_generate(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = _gemini_quota_exhausted_error()

    key2_client = Mock()
    key2_response = Mock()
    key2_response.text = json.dumps({
        "summary": "From the second key.",
        "experience_bullets": ["Bullet."],
        "skills_section": "Python",
    })
    key2_client.models.generate_content.return_value = key2_response

    mock_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    result = generate_enhanced_resume("resume text", [], {})

    assert result["source"] == "ai"
    assert result["summary"] == "From the second key."
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()


@patch("app.services.resume_builder.groq_client")
@patch("app.services.resume_builder.genai.Client")
def test_both_gemini_keys_quota_exhausted_falls_back_to_groq(mock_gemini_client_cls, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = _gemini_quota_exhausted_error()
    key2_client = Mock()
    key2_client.models.generate_content.side_effect = _gemini_quota_exhausted_error()
    mock_gemini_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = _mock_groq_response({
        "summary": "From Groq after both Gemini keys were exhausted.",
        "experience_bullets": ["Bullet."],
        "skills_section": "Python",
    })
    mock_groq_client_fn.return_value = mock_groq_client

    result = generate_enhanced_resume("resume text", [], {})

    assert result["source"] == "ai"
    assert "Groq" in result["summary"]
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()
    mock_groq_client.chat.completions.create.assert_called_once()


@patch("app.services.resume_builder.genai.Client")
def test_first_key_non_quota_error_never_tries_second_key(mock_client_cls, monkeypatch):
    """A real error (not a 429) on the first key must fail over to the
    deterministic fallback immediately -- never cascade to the second key or
    Groq, so a genuine bug can't hide behind extra providers."""
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = genai_errors.ClientError(
        400, {"message": "bad request", "status": "INVALID_ARGUMENT"}, None
    )
    key2_client = Mock()

    mock_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    result = generate_enhanced_resume("resume text", [], {})

    assert result["source"] == "fallback"
    key2_client.models.generate_content.assert_not_called()


@patch("app.services.resume_builder.genai.Client")
def test_second_gemini_key_used_when_first_hits_quota_for_chat(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    key1_client = Mock()
    key1_client.models.generate_content.side_effect = _gemini_quota_exhausted_error()

    key2_client = Mock()
    key2_response = Mock()
    key2_response.text = json.dumps({
        "reply": "Done — from the second key.",
        "summary": "Current summary.",
        "experience_bullets": ["Bullet one."],
        "skills_section": "Python, SQL",
    })
    key2_client.models.generate_content.return_value = key2_response

    mock_client_cls.side_effect = _two_key_client_factory(key1_client, key2_client)

    result = chat_about_resume(
        conversation=[{"role": "user", "content": "Remove the second bullet."}],
        resume_text="resume text",
        missing_skills=[],
        current_summary="Current summary.",
        current_experience_bullets=["Bullet one.", "Bullet two."],
        current_skills_section="Python, SQL",
    )

    assert result["source"] == "ai"
    assert "second key" in result["reply"]
    key1_client.models.generate_content.assert_called_once()
    key2_client.models.generate_content.assert_called_once()
