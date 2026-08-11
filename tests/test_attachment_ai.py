from unittest.mock import patch, Mock
from google.genai import errors as genai_errors
from app.services.attachment_ai import analyze_attachment

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"
DOCX_BYTES = b"fake-docx-bytes"


def test_ai_disabled_returns_no_description(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = analyze_attachment(PNG_BYTES, "image/png", "screenshot.png", ai_enabled=False)
    assert result["description"] is None
    assert result["source"] == "fallback"
    assert "disabled" in result["message"]


def test_no_api_key_image_returns_no_description(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    result = analyze_attachment(PNG_BYTES, "image/png", "screenshot.png")
    assert result["description"] is None
    assert "unavailable" in result["message"]


@patch("app.services.attachment_ai.genai.Client")
def test_image_successful_call_returns_ai_description(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = "This is a screenshot of a job posting for a Backend Engineer role requiring Python and AWS."
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = analyze_attachment(PNG_BYTES, "image/png", "job-posting.png", user_message="what does this say?")
    assert result["source"] == "ai"
    assert "Backend Engineer" in result["description"]
    # Confirms the binary was actually sent as inline data, not silently dropped.
    sent_contents = mock_client.models.generate_content.call_args.kwargs["contents"]
    assert len(sent_contents) == 2


@patch("app.services.attachment_ai.genai.Client")
def test_pdf_is_treated_as_natively_readable(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = "A certificate of completion for an AWS course."
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = analyze_attachment(b"%PDF-1.4 fake", "application/pdf", "certificate.pdf")
    assert result["source"] == "ai"
    assert "certificate" in result["description"].lower()


@patch("app.services.attachment_ai.genai.Client")
def test_image_quota_exhausted_returns_no_fallback(mock_client_cls, monkeypatch):
    """Groq's model is text-only — there's no vision fallback, so an exhausted Gemini quota
    must produce an honest failure, not a fabricated description."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    mock_client = Mock()
    mock_client.models.generate_content.side_effect = genai_errors.ClientError(
        429, {"message": "rate limited", "status": "RESOURCE_EXHAUSTED"}, None
    )
    mock_client_cls.return_value = mock_client

    with patch("app.services.attachment_ai.groq_client") as mock_groq_client_fn:
        result = analyze_attachment(PNG_BYTES, "image/png", "screenshot.png")
        assert result["description"] is None
        assert result["source"] == "fallback"
        mock_groq_client_fn.assert_not_called()


def test_unsupported_file_type_returns_clear_message(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = analyze_attachment(b"random bytes", "application/octet-stream", "archive.zip")
    assert result["description"] is None
    assert "unsupported" in result["message"].lower() or "upload" in result["message"].lower()


@patch("app.services.attachment_ai.extract_resume_text")
@patch("app.services.attachment_ai.genai.Client")
def test_docx_extracts_text_then_analyzes_it(mock_client_cls, mock_extract, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_extract.return_value = "John Doe — Senior Backend Engineer, 5 years Python experience."

    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = "A resume for John Doe, a Senior Backend Engineer with 5 years of Python experience."
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = analyze_attachment(DOCX_BYTES, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "resume.docx")
    assert result["source"] == "ai"
    assert "John Doe" in result["description"]
    mock_extract.assert_called_once_with("resume.docx", DOCX_BYTES)
    # The text path sends a single text prompt, not an inline-binary Part.
    sent_contents = mock_client.models.generate_content.call_args.kwargs["contents"]
    assert isinstance(sent_contents, str)


@patch("app.services.attachment_ai.extract_resume_text")
def test_docx_no_ai_falls_back_to_raw_extracted_text(mock_extract, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    mock_extract.return_value = "Some extracted resume text."

    result = analyze_attachment(DOCX_BYTES, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "resume.docx")
    assert result["source"] == "fallback"
    assert "Some extracted resume text." in result["description"]


@patch("app.services.attachment_ai.extract_resume_text")
def test_docx_extraction_failure_returns_message(mock_extract, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_extract.side_effect = ValueError("Unsupported file type. Please upload PDF, DOCX, TXT, PNG, or JPG.")

    result = analyze_attachment(b"bad bytes", "application/msword", "notes.doc")
    assert result["description"] is None
    assert "Unsupported file type" in result["message"]


@patch("app.services.attachment_ai.groq_client")
@patch("app.services.attachment_ai.extract_resume_text")
@patch("app.services.attachment_ai.genai.Client")
def test_docx_gemini_quota_falls_back_to_groq(mock_gemini_client_cls, mock_extract, mock_groq_client_fn, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    mock_extract.return_value = "Extracted document text."

    mock_gemini_client = Mock()
    mock_gemini_client.models.generate_content.side_effect = genai_errors.ClientError(
        429, {"error": {"code": 429, "message": "quota exceeded", "status": "RESOURCE_EXHAUSTED", "details": []}}, None
    )
    mock_gemini_client_cls.return_value = mock_gemini_client

    mock_groq_response = Mock()
    mock_groq_response.choices = [Mock(message=Mock(content="A summary from Groq."))]
    mock_groq_client = Mock()
    mock_groq_client.chat.completions.create.return_value = mock_groq_response
    mock_groq_client_fn.return_value = mock_groq_client

    result = analyze_attachment(DOCX_BYTES, "text/plain", "notes.txt")
    assert result["source"] == "ai"
    assert result["description"] == "A summary from Groq."
