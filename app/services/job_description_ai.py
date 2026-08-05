"""
AI-powered job description parsing. Follows the same shape as the rest of
this app's AI services (ai_suggestions.py, resume_builder.py): Gemini SDK, a
GEMINI_API_KEY gate, structured JSON output, and a rule-based fallback (see
app/services/job_description_parser.py) when AI is disabled/unavailable.

The rule-based fallback extracts "required skills" via raw word-frequency
counting, which surfaces generic filler words ("developer", "team", "role")
alongside — or instead of — real skills. This service asks Gemini to read
the posting like a person would and name the actual skills, experience
requirement, and qualifications, which is what makes resume-to-job matching
meaningful rather than keyword noise.

For content extracted from a URL/file, `cleaned_description` is the AI's
extraction of just the actual job posting — title, responsibilities,
requirements — with site chrome (navigation, related postings, cookie
banners, footers) stripped out, so the frontend can prefill the full JD
text field with something usable instead of a raw scrape.
"""
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

JD_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "experience_level": {"type": "string"},
        "qualifications": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "cleaned_description": {"type": "string"},
    },
    "required": ["title", "required_skills", "experience_level", "qualifications", "keywords", "cleaned_description"],
    "additionalProperties": False,
}


def _build_prompt(text: str) -> str:
    return f"""The following text was scraped from a job posting page (it may include unrelated site content like
navigation, cookie notices, related postings, or footer text mixed in with the actual posting). Read it and extract:

- title: the job title being advertised. Empty string if genuinely not present.
- required_skills: the REAL, specific technical and professional skills this role requires (e.g. "Python",
  "AWS", "stakeholder management", "SQL") — actual named skills, never generic words like "team", "role",
  "experience", "our", or sentence fragments. Only include a skill if the posting genuinely asks for it.
- experience_level: a short phrase describing the experience required (e.g. "3+ years", "Senior", "Entry-level").
  "Not specified" if the posting doesn't say.
- qualifications: degrees, certifications, or licenses mentioned (e.g. "Bachelor's degree in Computer Science").
  Empty list if none mentioned.
- keywords: 15-30 other relevant terms from the posting useful for resume keyword matching (tools, methodologies,
  domain terms) — real words/phrases from the posting, not generic filler.
- cleaned_description: the actual job posting content only (title, summary, responsibilities, requirements,
  qualifications) — rewritten as clean plain text, with all unrelated site chrome (navigation, cookie banners,
  "related jobs", footer/legal boilerplate, ads) removed. Preserve the real content faithfully; don't summarize
  or shorten it, just clean it up.

Scraped text:
{text[:8000]}
"""


def _parse_via_groq(text: str) -> dict:
    """Groq equivalent of the Gemini call in parse_job_description_ai — same
    prompt (reuses _build_prompt exactly), adapted only in how the JSON shape
    is requested/parsed."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_prompt(text) + groq_json_instructions(
        '"title" (string), "required_skills" (array of strings), "experience_level" (string), '
        '"qualifications" (array of strings), "keywords" (array of strings), "cleaned_description" (string)'
    )

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    if not result.get("required_skills"):
        raise ValueError("Groq response had no required_skills")
    return result


def _try_groq_parse(text: str) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing rule-based fallback instead of surfacing an error."""
    try:
        result = _parse_via_groq(text)
        logger.info("job_description_ai.parse_job_description_ai served by groq (gemini quota/rate-limit hit)")
        return result
    except Exception:
        logger.warning("job_description_ai.parse_job_description_ai: groq fallback also failed", exc_info=True)
        return None


def parse_job_description_ai(text: str, ai_enabled: bool = True) -> dict | None:
    """Returns {"title", "required_skills", "experience_level", "qualifications",
    "keywords", "cleaned_description"}, or None if AI is unavailable/disabled/
    fails — callers should fall back to job_description_parser.parse_job_description."""
    if not ai_enabled or not text or not text.strip():
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        client = _client(api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=_build_prompt(text),
            config=genai_types.GenerateContentConfig(
                max_output_tokens=4096,
                response_mime_type="application/json",
                response_json_schema=JD_SCHEMA,
                thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
            ),
        )
        result = json.loads(response.text)
        if not result.get("required_skills"):
            return None
        logger.info("job_description_ai.parse_job_description_ai served by gemini")
        return result
    except genai_errors.ClientError as e:
        if e.code == 429:
            groq_result = _try_groq_parse(text)
            if groq_result is not None:
                return groq_result
        logger.info("job_description_ai.parse_job_description_ai served by fallback (gemini ClientError, code=%s)", e.code)
        return None
    except Exception:
        logger.info("job_description_ai.parse_job_description_ai served by fallback (unexpected gemini error)")
        return None
