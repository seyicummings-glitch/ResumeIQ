import os
import json
import logging
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-latest"

# The SDK's default retry policy (5 attempts, exponential backoff up to 60s) is
# meant for transient errors — but a 429 caused by the daily quota being fully
# exhausted will never succeed no matter how many times it's retried within
# that window, so it just adds up to ~60s of dead time before falling back.
# Capping attempts keeps that worst case short.
_RETRY_OPTIONS = genai_types.HttpRetryOptions(attempts=2)


def _client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key, http_options=genai_types.HttpOptions(retry_options=_RETRY_OPTIONS))


# --- Groq fallback -----------------------------------------------------------
# Automatic second provider for when Gemini's quota/rate-limit is hit (429).
# Uses Groq's OpenAI-compatible endpoint via the `openai` SDK. This only ever
# triggers on a Gemini 429 — any other kind of Gemini failure (bad request,
# server error, etc.) is a real bug and must keep failing over to the existing
# deterministic fallback exactly as before, not mask itself behind a second
# provider. If Groq itself also fails for any reason, callers treat that the
# same as "no AI available" and fall through to the existing fallback path —
# the user always gets a usable response, never a raw error.
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# Groq is already a fallback reached after Gemini used its own retry budget —
# don't stack a second multi-attempt retry loop on top of that; one retry is
# enough headroom for a transient blip without adding much latency.
_GROQ_MAX_RETRIES = 1


def _groq_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL, max_retries=_GROQ_MAX_RETRIES)


def _groq_json_instructions(keys_description: str) -> str:
    return (
        f"\n\nRespond with ONLY a single JSON object (no markdown fences, no commentary before or after) "
        f"with exactly these keys: {keys_description}"
    )


def _generate_via_groq(resume_text: str, missing_skills: list[str]) -> dict:
    """Groq equivalent of the Gemini call in generate_enhanced_resume — same
    prompt/grounding/anti-fabrication rules (reuses _build_prompt exactly),
    adapted only in how the JSON shape is requested and parsed, since Groq's
    OpenAI-compatible API has JSON *mode* but not Gemini's strict
    response_json_schema enforcement."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_prompt(resume_text, missing_skills) + _groq_json_instructions(
        '"summary" (string), "experience_bullets" (array of strings), "skills_section" (string)'
    )

    client = _groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        # Matches the token budget used for the equivalent Gemini call.
        max_tokens=6000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    for key in ("summary", "experience_bullets", "skills_section"):
        if key not in result:
            raise ValueError(f"Groq response missing required key: {key}")
    result["source"] = "ai"
    return result


def _try_groq_generate(resume_text: str, missing_skills: list[str]) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing deterministic fallback instead of surfacing an error."""
    try:
        result = _generate_via_groq(resume_text, missing_skills)
        logger.info("resume_builder.generate_enhanced_resume served by groq (gemini quota/rate-limit hit)")
        return result
    except Exception:
        logger.warning("resume_builder.generate_enhanced_resume: groq fallback also failed", exc_info=True)
        return None


def _chat_via_groq(
    conversation: list[dict],
    resume_text: str,
    missing_skills: list[str],
    current_summary: str,
    current_experience_bullets: list[str],
    current_skills_section: str,
) -> dict:
    """Groq equivalent of the Gemini call in chat_about_resume — same grounding/
    draft-state/anti-fabrication system prompt (reuses _build_chat_system_prompt
    exactly) and the same conversation history, adapted only in transport
    (Gemini's role/parts content format vs. OpenAI-style messages) and how the
    JSON shape is requested."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    system_prompt = _build_chat_system_prompt(
        resume_text, missing_skills, current_summary, current_experience_bullets, current_skills_section
    ) + _groq_json_instructions(
        '"reply" (string), "summary" (string), "experience_bullets" (array of strings), "skills_section" (string)'
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": "assistant" if m["role"] == "assistant" else "user", "content": m["content"]} for m in conversation
    )
    if not conversation:
        messages.append({"role": "user", "content": "Please begin."})

    client = _groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=6000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    for key in ("reply", "summary", "experience_bullets", "skills_section"):
        if key not in result:
            raise ValueError(f"Groq response missing required key: {key}")
    result["source"] = "ai"
    return result


def _try_groq_chat(
    conversation: list[dict],
    resume_text: str,
    missing_skills: list[str],
    current_summary: str,
    current_experience_bullets: list[str],
    current_skills_section: str,
) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing deterministic fallback instead of surfacing an error."""
    try:
        result = _chat_via_groq(
            conversation, resume_text, missing_skills, current_summary, current_experience_bullets, current_skills_section
        )
        logger.info("resume_builder.chat_about_resume served by groq (gemini quota/rate-limit hit)")
        return result
    except Exception:
        logger.warning("resume_builder.chat_about_resume: groq fallback also failed", exc_info=True)
        return None
# --- end Groq fallback --------------------------------------------------------


def _is_daily_quota_error(e: genai_errors.ClientError) -> bool:
    """Gemini returns 429 for both a genuine short-term rate limit (retry in a few
    seconds) and the account's daily request quota being exhausted (won't recover
    until it resets, or until billing is enabled) — this tells them apart so the
    user isn't told "give it a moment" when a moment won't actually fix anything."""
    try:
        details = e.details.get("error", {}).get("details", [])
    except AttributeError:
        return False
    for entry in details:
        for violation in entry.get("violations", []):
            if "PerDay" in violation.get("quotaId", ""):
                return True
    return False

BUILDER_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "experience_bullets": {
            "type": "array",
            "items": {"type": "string"}
        },
        "skills_section": {"type": "string"}
    },
    "required": ["summary", "experience_bullets", "skills_section"],
    "additionalProperties": False
}


def _build_prompt(resume_text: str, missing_skills: list[str]) -> str:
    prompt = (
        "You are an expert resume writer. Rewrite the following resume to make it stronger, "
        "using ONLY the experience and facts already present in the resume text below.\n\n"
        "Do the following:\n"
        "1. Rewrite the professional summary to be sharper and more compelling (2-4 sentences).\n"
        "2. Rewrite up to 6 of the strongest experience bullet points to be more quantified and "
        "impactful (use metrics/numbers only if they are already implied or present in the original "
        "text — do not invent statistics).\n"
        "3. Produce a reorganized, categorized skills section (e.g. grouped by category such as "
        "'Languages', 'Frameworks', 'Tools', etc., as appropriate).\n\n"
        "CRITICAL RULE: Never fabricate skills, credentials, employers, titles, or accomplishments the "
        "person does not plausibly have. Do not claim experience with a technology unless the resume "
        "already shows evidence of related, transferable experience.\n\n"
        f"Resume:\n{resume_text[:6000]}"
    )

    if missing_skills:
        skills_list = ", ".join(missing_skills)
        prompt += (
            f"\n\nThe following skills were identified as missing when this resume was matched against "
            f"a target job: {skills_list}. If — and only if — the resume shows genuinely related or "
            "transferable experience for any of these skills, you may naturally incorporate that skill "
            "into the skills section or an experience bullet, phrased honestly (e.g. 'exposure to', "
            "'familiarity with') rather than claiming deep expertise. Do NOT add a skill if there is no "
            "plausible basis for it anywhere in the resume — it is far better to omit a missing skill "
            "than to fabricate a claim."
        )

    return prompt


def generate_enhanced_resume(resume_text: str, missing_skills: list[str], fallback_data: dict, ai_enabled: bool = True) -> dict:
    """Call Gemini to produce an enhanced summary/experience/skills section for a resume.
    Falls back to a deterministic, lightly-reformatted version of the original content if the
    API key is missing, AI features have been disabled platform-wide (ai_enabled=False, set via
    Admin Settings), or the call fails. Uses the free-tier Gemini API (server-wide GEMINI_API_KEY
    env var) rather than a per-user key."""
    if not ai_enabled:
        return _fallback_response("AI resume building has been disabled by the administrator.", fallback_data)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_response("AI resume building is not configured (no API key set).", fallback_data)

    try:
        client = _client(api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=_build_prompt(resume_text, missing_skills),
            config=genai_types.GenerateContentConfig(
                # 2048 wasn't enough headroom once the model's internal "thinking"
                # tokens are counted against the same budget — this raises it the
                # same way the skill-assessment and interviewer services were fixed.
                max_output_tokens=6000,
                thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                response_mime_type="application/json",
                response_json_schema=BUILDER_SCHEMA,
            ),
        )
        result = json.loads(response.text)
        result["source"] = "ai"
        logger.info("resume_builder.generate_enhanced_resume served by gemini")
        return result
    except genai_errors.ClientError as e:
        if e.code == 429:
            groq_result = _try_groq_generate(resume_text, missing_skills)
            if groq_result is not None:
                return groq_result
            if _is_daily_quota_error(e):
                return _fallback_response(
                    "AI resume building has hit its daily usage limit — it'll be back once that resets, or "
                    "once an admin upgrades the AI plan. Showing your original content instead.",
                    fallback_data,
                )
            return _fallback_response("AI resume building is temporarily rate-limited. Showing your original content instead.", fallback_data)
        return _fallback_response("The AI service returned an error. Showing your original content instead.", fallback_data)
    except genai_errors.ServerError:
        return _fallback_response("Could not reach the AI service. Showing your original content instead.", fallback_data)
    except Exception:
        return _fallback_response("AI resume building is temporarily unavailable. Showing your original content instead.", fallback_data)


CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "summary": {"type": "string"},
        "experience_bullets": {
            "type": "array",
            "items": {"type": "string"}
        },
        "skills_section": {"type": "string"}
    },
    "required": ["reply", "summary", "experience_bullets", "skills_section"],
    "additionalProperties": False
}


def _build_chat_system_prompt(
    resume_text: str,
    missing_skills: list[str],
    current_summary: str,
    current_experience_bullets: list[str],
    current_skills_section: str,
) -> str:
    bullets_text = "\n".join(f"- {b}" for b in current_experience_bullets) if current_experience_bullets else "(none)"
    skills_list = ", ".join(missing_skills) if missing_skills else "none noted"
    has_draft = bool(current_summary or current_experience_bullets or current_skills_section)

    if resume_text:
        grounding = (
            f"The user has a saved resume you can draw on (they may also give you new information "
            f"directly in chat — combine both):\n{resume_text[:4000]}"
        )
    else:
        grounding = (
            "The user hasn't uploaded or saved a resume yet. Build their resume from what they tell you "
            "in this conversation instead — ask about their target role, work history, and skills if you "
            "don't have enough yet. They can also upload an existing CV at any point using the upload "
            "control, which becomes your grounding source from then on."
        )

    draft_state = (
        f"Summary: {current_summary}\nExperience bullets:\n{bullets_text}\nSkills section: {current_skills_section}"
        if has_draft
        else "(nothing drafted yet)"
    )

    return (
        "You are an AI resume-building assistant having a conversation with the user to help them build "
        "a new resume or edit an existing one.\n\n"
        f"{grounding}\n\n"
        f"Skills identified as missing against a target job (if any): {skills_list}\n\n"
        f"Current draft of the resume you're building/editing together:\n{draft_state}\n\n"
        "The user will ask you to add, remove, or change parts of this draft, describe their background "
        "for you to turn into resume content, or ask general questions. Apply requests to the CURRENT "
        "DRAFT above, building on it incrementally.\n\n"
        "Rules:\n"
        "- Never fabricate skills, credentials, employers, titles, or accomplishments — only include what "
        "the user has told you (via a saved resume or this conversation) or what's plausibly implied by "
        "it.\n"
        "- If you don't yet have enough real information to write or update a section, don't invent "
        "placeholder content — ask the user for the details instead, and leave that section unchanged in "
        "the draft.\n"
        "- Keep your conversational reply short (1-4 sentences).\n"
        "- Always return the FULL current state of the resume (summary, all experience bullets, full "
        "skills section) in the structured fields, reflecting any changes from this turn — even fields "
        "you didn't touch."
    )


def chat_about_resume(
    conversation: list[dict],
    resume_text: str,
    missing_skills: list[str],
    current_summary: str,
    current_experience_bullets: list[str],
    current_skills_section: str,
    ai_enabled: bool = True,
) -> dict:
    """One turn of AI-assisted, conversational resume editing. conversation is a list of
    {"role": "user"|"assistant", "content": str} in chronological order, not including the reply
    being generated now. Uses the free-tier Gemini API (server-wide GEMINI_API_KEY env var).
    Resume chat editing has no rule-based equivalent, so if AI is disabled/unavailable the draft
    is returned unchanged with an explanatory reply rather than a fabricated edit."""
    unavailable_reply = {
        "reply": (
            "AI resume chat isn't available right now — the AI service isn't configured. You can still "
            "use the one-shot Generate button, or edit the text directly."
        ),
        "summary": current_summary,
        "experience_bullets": current_experience_bullets,
        "skills_section": current_skills_section,
        "source": "fallback",
    }

    if not ai_enabled:
        unavailable_reply["reply"] = "AI resume chat has been disabled by the administrator."
        logger.info("resume_builder.chat_about_resume served by fallback (AI disabled by admin)")
        return unavailable_reply

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.info("resume_builder.chat_about_resume served by fallback (no GEMINI_API_KEY configured)")
        return unavailable_reply

    try:
        client = _client(api_key)
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in conversation
        ]
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=6000,
                thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                system_instruction=_build_chat_system_prompt(
                    resume_text, missing_skills, current_summary, current_experience_bullets, current_skills_section
                ),
                response_mime_type="application/json",
                response_json_schema=CHAT_SCHEMA,
            ),
        )
        result = json.loads(response.text)
        result["source"] = "ai"
        logger.info("resume_builder.chat_about_resume served by gemini")
        return result
    except genai_errors.ClientError as e:
        if e.code == 429:
            groq_result = _try_groq_chat(
                conversation, resume_text, missing_skills, current_summary, current_experience_bullets, current_skills_section
            )
            if groq_result is not None:
                return groq_result

        error_reply = dict(unavailable_reply)
        if e.code == 429:
            error_reply["reply"] = (
                "The AI assistant has hit its daily usage limit — it'll be back once that resets, or once an "
                "admin upgrades the AI plan. Your draft wasn't changed; you can still edit it directly."
                if _is_daily_quota_error(e)
                else "You're sending messages a bit fast — give it a moment and try again."
            )
        else:
            error_reply["reply"] = "The AI service returned an error — your draft wasn't changed. Try rephrasing your request."
        logger.info("resume_builder.chat_about_resume served by fallback (gemini ClientError, code=%s)", e.code)
        return error_reply
    except genai_errors.ServerError:
        error_reply = dict(unavailable_reply)
        error_reply["reply"] = "Could not reach the AI service — your draft wasn't changed. Try again in a moment."
        logger.info("resume_builder.chat_about_resume served by fallback (gemini ServerError)")
        return error_reply
    except Exception:
        error_reply = dict(unavailable_reply)
        error_reply["reply"] = "Something went wrong generating a reply — your draft wasn't changed."
        logger.info("resume_builder.chat_about_resume served by fallback (unexpected error)")
        return error_reply


def _fallback_response(message: str, fallback_data: dict) -> dict:
    logger.info("resume_builder.generate_enhanced_resume served by fallback (%s)", message)
    original_summary = (fallback_data.get("original_summary") or "").strip()
    original_experience = (fallback_data.get("original_experience") or "").strip()
    original_skills = fallback_data.get("original_skills") or []

    summary = original_summary if original_summary else "No professional summary was found on your resume."

    if original_experience:
        raw_lines = [line.strip(" -•\t") for line in original_experience.split("\n") if line.strip()]
        experience_bullets = raw_lines[:6] if raw_lines else [original_experience]
    else:
        experience_bullets = ["No experience bullets were found on your resume."]

    if original_skills:
        skills_section = ", ".join(original_skills)
    else:
        skills_section = "No skills were found on your resume."

    return {
        "summary": summary,
        "experience_bullets": experience_bullets,
        "skills_section": skills_section,
        "overall_assessment": message,
        "source": "fallback"
    }
