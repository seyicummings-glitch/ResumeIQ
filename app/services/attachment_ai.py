"""
Multimodal file attachment analysis for the AI Resume Builder — lets a user drop an image,
screenshot, PDF, or document straight into the conversation the way they would with ChatGPT,
Claude, or Gemini. Runs once per attachment (not resent on every later turn): Gemini reads the
file directly — genuine vision for images and native PDF understanding, not just OCR — and
produces a rich text description, which is then folded into the conversation like anything else
the user said. That keeps the rest of the chat architecture (full text history resent each
turn, see resume_builder.py) unchanged; only the attachment step itself is multimodal.

Images and PDFs go to Gemini as raw bytes (its structured-output multimodal input). Other
document types (.docx, .txt) aren't something Gemini accepts as inline binary, so their text is
extracted first (reusing resume_parser.py, which already does this for resume uploads) and then
analyzed as text — which also means, unlike the vision path, a Groq fallback is possible for
those when Gemini's quota is exhausted.
"""
import os
import logging
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from app.services.groq_client import GROQ_MODEL, groq_client
from app.services.resume_parser import extract_resume_text

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-latest"

_RETRY_OPTIONS = genai_types.HttpRetryOptions(attempts=2)

# Formats Gemini accepts as inline binary (real vision / native PDF understanding). Anything
# else falls back to text extraction first.
_NATIVE_MIME_PREFIXES = ("image/", "application/pdf")

_ANALYSIS_INSTRUCTIONS = (
    "Describe everything in this file that would be relevant to a resume-building or career "
    "conversation. Transcribe any visible text verbatim (job titles, dates, company names, "
    "certifications, job posting requirements, error messages, etc.), describe layout or "
    "visual design if relevant (e.g. a resume template, a UI screenshot), and summarize the "
    "overall content and purpose of the file. Be thorough and specific — this description is "
    "the only record of the file's content for the rest of the conversation."
)


def _client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key, http_options=genai_types.HttpOptions(retry_options=_RETRY_OPTIONS))


def _gemini_api_keys() -> list[str]:
    return [k for k in [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")] if k]


def _is_natively_readable(mime_type: str) -> bool:
    return any(mime_type.startswith(prefix) for prefix in _NATIVE_MIME_PREFIXES)


def _build_prompt_text(filename: str, user_message: str | None) -> str:
    context = f'The user attached a file named "{filename}"'
    if user_message:
        context += f' and said: "{user_message}"'
    else:
        context += " with no accompanying message"
    return f"{context}.\n\n{_ANALYSIS_INSTRUCTIONS}"


def _analyze_multimodal(file_bytes: bytes, mime_type: str, filename: str, user_message: str | None) -> str | None:
    """Vision/native-PDF path — no Groq fallback exists for this (Groq's model is text-only),
    so this returns None on any failure and the caller decides what to tell the user."""
    gemini_keys = _gemini_api_keys()
    if not gemini_keys:
        return None

    prompt = _build_prompt_text(filename, user_message)
    for api_key in gemini_keys:
        try:
            client = _client(api_key)
            response = client.models.generate_content(
                model=MODEL,
                contents=[
                    genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                    genai_types.Part.from_text(text=prompt),
                ],
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=2000,
                    thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                ),
            )
            logger.info("attachment_ai.analyze_attachment served by gemini (multimodal, mime=%s)", mime_type)
            return response.text
        except genai_errors.ClientError as e:
            if e.code == 429:
                continue
            logger.info("attachment_ai.analyze_attachment failed (gemini ClientError, code=%s)", e.code)
            return None
        except Exception:
            logger.info("attachment_ai.analyze_attachment failed (unexpected gemini error)", exc_info=True)
            return None

    logger.info("attachment_ai.analyze_attachment: all gemini keys quota/rate-limited, no vision fallback available")
    return None


def _analyze_text(text: str, filename: str, user_message: str | None) -> str | None:
    """Text path (for extracted .docx/.txt content) — has a Groq fallback since it's plain text."""
    prompt = _build_prompt_text(filename, user_message) + f"\n\nExtracted file content:\n{text[:8000]}"

    gemini_keys = _gemini_api_keys()
    for api_key in gemini_keys:
        try:
            client = _client(api_key)
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=2000,
                    thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                ),
            )
            logger.info("attachment_ai.analyze_attachment served by gemini (text, filename=%s)", filename)
            return response.text
        except genai_errors.ClientError as e:
            if e.code == 429:
                continue
            return None
        except Exception:
            return None

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return None
    try:
        client = groq_client(groq_api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )
        logger.info("attachment_ai.analyze_attachment served by groq (text, filename=%s)", filename)
        return response.choices[0].message.content
    except Exception:
        logger.warning("attachment_ai.analyze_attachment: groq fallback also failed", exc_info=True)
        return None


def analyze_attachment(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
    user_message: str | None = None,
    ai_enabled: bool = True,
) -> dict:
    """Analyzes an uploaded image, screenshot, PDF, or document and returns a rich text
    description to fold into the AI Resume Builder conversation. Returns
    {"description": str|None, "source": "ai"|"fallback", "message": str|None} — description is
    None only when analysis genuinely couldn't happen (AI disabled/unavailable), in which case
    `message` explains why so the caller can tell the user honestly rather than pretending it
    worked."""
    if not ai_enabled:
        return {"description": None, "source": "fallback", "message": "File analysis has been disabled by the administrator."}

    if _is_natively_readable(mime_type):
        description = _analyze_multimodal(file_bytes, mime_type, filename, user_message)
        if description is not None:
            return {"description": description, "source": "ai", "message": None}
        return {
            "description": None,
            "source": "fallback",
            "message": "Couldn't analyze this file's content right now — the AI vision service is unavailable. You can describe what's in it instead.",
        }

    try:
        extracted_text = extract_resume_text(filename, file_bytes)
    except ValueError as e:
        return {"description": None, "source": "fallback", "message": str(e)}

    if not extracted_text or not extracted_text.strip():
        return {
            "description": None,
            "source": "fallback",
            "message": "Couldn't extract any readable content from this file.",
        }

    description = _analyze_text(extracted_text, filename, user_message)
    if description is not None:
        return {"description": description, "source": "ai", "message": None}

    # No AI available at all for the text path either — the raw extracted text is still
    # genuinely useful context, so hand that back rather than nothing.
    return {
        "description": f"(AI analysis unavailable — raw extracted text follows)\n\n{extracted_text[:4000]}",
        "source": "fallback",
        "message": None,
    }
