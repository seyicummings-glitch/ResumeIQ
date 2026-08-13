"""Shared Groq client setup, used by every AI service as an automatic fallback
when Gemini returns a 429 (daily quota exhausted or a short-term rate limit).
Groq is reached via its OpenAI-compatible endpoint through the `openai` SDK.

Each service builds its own prompts/schemas and does its own JSON parsing
(same as it already does for Gemini) — this module only holds the bits that
are identical everywhere: which model, which endpoint, and how many retries
Groq itself gets.
"""
from openai import OpenAI

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Groq is already a fallback reached after Gemini used its own retry budget —
# don't stack a second multi-attempt retry loop on top of that; one retry is
# enough headroom for a transient blip without adding much latency.
GROQ_MAX_RETRIES = 1


def groq_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL, max_retries=GROQ_MAX_RETRIES)


def groq_json_instructions(keys_description: str) -> str:
    """Appended to a prompt to request Groq's JSON *mode* output match a specific
    shape — Groq's OpenAI-compatible API guarantees valid JSON syntax via
    response_format={"type": "json_object"}, but not a specific schema the way
    Gemini's response_json_schema does, so the required keys are spelled out
    in the prompt and the caller validates them after parsing."""
    return (
        f"\n\nRespond with ONLY a single JSON object (no markdown fences, no commentary before or after) "
        f"with exactly these keys: {keys_description}"
    )
