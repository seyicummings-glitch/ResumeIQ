import os
import json
import logging
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from app.services.groq_client import GROQ_MODEL, groq_client, groq_json_instructions

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-latest"

# The SDK's default retry policy (5 attempts, exponential backoff up to 60s) is
# meant for transient errors — but a 429 caused by the daily quota being fully
# exhausted will never succeed no matter how many times it's retried within
# that window, so it just adds up to ~60s of dead time before even reaching
# the Groq fallback below. Capping attempts keeps that worst case short.
_RETRY_OPTIONS = genai_types.HttpRetryOptions(attempts=2)


def _client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key, http_options=genai_types.HttpOptions(retry_options=_RETRY_OPTIONS))

SUGGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_assessment": {"type": "string"},
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"}
                },
                "required": ["category", "issue", "suggestion"],
                "additionalProperties": False
            }
        }
    },
    "required": ["overall_assessment", "suggestions"],
    "additionalProperties": False
}


def _build_prompt(resume_text: str, job_description: str | None) -> str:
    prompt = f"Review this resume and give specific, actionable improvement suggestions.\n\nResume:\n{resume_text[:6000]}"
    if job_description:
        prompt += f"\n\nTailor suggestions toward this target job description:\n{job_description[:3000]}"
    return prompt


def _suggestions_via_groq(resume_text: str, job_description: str | None) -> dict:
    """Groq equivalent of the Gemini call in generate_resume_suggestions — same
    prompt (reuses _build_prompt exactly), adapted only in how the JSON shape
    is requested/parsed."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_prompt(resume_text, job_description) + groq_json_instructions(
        '"overall_assessment" (string), "suggestions" (array of objects each with "category" (string), '
        '"issue" (string), "suggestion" (string))'
    )

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    if "overall_assessment" not in result or "suggestions" not in result:
        raise ValueError("Groq response missing required keys")
    return result


def _try_groq_suggestions(resume_text: str, job_description: str | None) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing rule-based fallback instead of surfacing an error."""
    try:
        result = _suggestions_via_groq(resume_text, job_description)
        result["source"] = "ai"
        logger.info("ai_suggestions.generate_resume_suggestions served by groq (gemini quota/rate-limit hit)")
        return result
    except Exception:
        logger.warning("ai_suggestions.generate_resume_suggestions: groq fallback also failed", exc_info=True)
        return None


def generate_resume_suggestions(resume_text: str, job_description: str | None, fallback_data: dict, ai_enabled: bool = True) -> dict:
    """Call Gemini for resume improvement suggestions. Falls back to existing rule-based
    analysis (ATS score / keyword match issues) if the server-wide GEMINI_API_KEY isn't set,
    AI features have been disabled platform-wide (ai_enabled=False, set via Admin Settings),
    or the call fails."""
    if not ai_enabled:
        return _fallback_response("AI suggestions have been disabled by the administrator.", fallback_data)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_response("AI suggestions are not configured (no API key set).", fallback_data)

    try:
        client = _client(api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=_build_prompt(resume_text, job_description),
            config=genai_types.GenerateContentConfig(
                # 1024 wasn't enough headroom once the model's internal "thinking"
                # tokens are counted against the same budget — raised the same way
                # the other AI services in this app were fixed.
                max_output_tokens=4000,
                response_mime_type="application/json",
                response_json_schema=SUGGESTION_SCHEMA,
                thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
            ),
        )
        result = json.loads(response.text)
        result["source"] = "ai"
        logger.info("ai_suggestions.generate_resume_suggestions served by gemini")
        return result
    except genai_errors.ClientError as e:
        if e.code == 429:
            groq_result = _try_groq_suggestions(resume_text, job_description)
            if groq_result is not None:
                return groq_result
            return _fallback_response("AI suggestions are temporarily rate-limited. Showing rule-based analysis instead.", fallback_data)
        return _fallback_response("The AI service returned an error. Showing rule-based analysis instead.", fallback_data)
    except genai_errors.ServerError:
        return _fallback_response("Could not reach the AI service. Showing rule-based analysis instead.", fallback_data)
    except Exception:
        return _fallback_response("AI suggestions are temporarily unavailable. Showing rule-based analysis instead.", fallback_data)


def _fallback_response(message: str, fallback_data: dict) -> dict:
    suggestions = []
    for issue in fallback_data.get("ats_issues", []):
        suggestions.append({"category": "ATS Compatibility", "issue": issue, "suggestion": "Address this to improve ATS parseability."})
    for skill in fallback_data.get("missing_keywords", [])[:10]:
        suggestions.append({"category": "Keywords", "issue": f"'{skill}' not found in resume", "suggestion": f"Consider adding '{skill}' if it genuinely applies to your experience."})

    return {
        "overall_assessment": message,
        "suggestions": suggestions,
        "source": "fallback"
    }
