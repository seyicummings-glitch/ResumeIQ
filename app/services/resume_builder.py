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
# that window, so it just adds up to ~60s of dead time before falling back.
# Capping attempts keeps that worst case short.
_RETRY_OPTIONS = genai_types.HttpRetryOptions(attempts=2)


def _client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key, http_options=genai_types.HttpOptions(retry_options=_RETRY_OPTIONS))


def _gemini_api_keys() -> list[str]:
    """A second Gemini key (GEMINI_API_KEY_2, e.g. from a different Google
    account) is optional extra daily quota tried before falling through to
    Groq — most installs will only have the first key set, in which case this
    behaves exactly as if there were only ever one."""
    return [k for k in [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")] if k]


# ---------------------------------------------------------------------------
# Output shape — a real, structured resume (headline, summary, skills, one
# entry per job with its own title/company/dates/bullets, education,
# certifications) rather than a flat summary/bullets/skills-blob. Contact
# info (name, email, phone, LinkedIn, location) is deliberately NOT part of
# this schema — it's never AI-generated; app/routes/resume_builder.py fills
# it in straight from the user's own profile fields, which is both more
# reliable and structurally prevents the AI from ever inventing someone's
# contact details.
# ---------------------------------------------------------------------------

_EXPERIENCE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "company": {"type": "string"},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "bullets": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "company", "start_date", "end_date", "bullets"],
    "additionalProperties": False,
}

_EDUCATION_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "degree": {"type": "string"},
        "school": {"type": "string"},
        "date": {"type": "string"},
    },
    "required": ["degree", "school", "date"],
    "additionalProperties": False,
}

_RESUME_FIELDS = {
    "title": {"type": "string"},
    "summary": {"type": "string"},
    "skills": {"type": "array", "items": {"type": "string"}},
    "experience": {"type": "array", "items": _EXPERIENCE_ITEM_SCHEMA},
    "education": {"type": "array", "items": _EDUCATION_ITEM_SCHEMA},
    "certifications": {"type": "array", "items": {"type": "string"}},
}
_RESUME_FIELD_KEYS = list(_RESUME_FIELDS.keys())

BUILDER_SCHEMA = {
    "type": "object",
    "properties": dict(_RESUME_FIELDS),
    "required": _RESUME_FIELD_KEYS,
    "additionalProperties": False,
}

CHAT_SCHEMA = {
    "type": "object",
    "properties": {"reply": {"type": "string"}, **_RESUME_FIELDS},
    "required": ["reply"] + _RESUME_FIELD_KEYS,
    "additionalProperties": False,
}

_GROQ_RESUME_FIELDS_SPEC = (
    '"title" (string — a professional headline like "Marketing & Sales Professional"), '
    '"summary" (string), "skills" (array of strings, one per skill — not grouped text), '
    '"experience" (array of objects, one per job, each with "title" (string), "company" (string), '
    '"start_date" (string), "end_date" (string, "Present" if current), "bullets" (array of strings)), '
    '"education" (array of objects, each with "degree" (string), "school" (string), "date" (string)), '
    '"certifications" (array of strings)'
)


# --- Groq fallback -----------------------------------------------------------
# Automatic second provider for when Gemini's quota/rate-limit is hit (429).
# Uses Groq's OpenAI-compatible endpoint via the `openai` SDK (see
# app/services/groq_client.py for the shared client/constants used by every
# AI service). This only ever triggers on a Gemini 429 — any other kind of
# Gemini failure (bad request, server error, etc.) is a real bug and must
# keep failing over to the existing deterministic fallback exactly as before,
# not mask itself behind a second provider. If Groq itself also fails for any
# reason, callers treat that the same as "no AI available" and fall through
# to the existing fallback path — the user always gets a usable response,
# never a raw error.


def _generate_via_groq(resume_text: str, missing_skills: list[str]) -> dict:
    """Groq equivalent of the Gemini call in generate_enhanced_resume — same
    prompt/grounding/anti-fabrication rules (reuses _build_prompt exactly),
    adapted only in how the JSON shape is requested and parsed, since Groq's
    OpenAI-compatible API has JSON *mode* but not Gemini's strict
    response_json_schema enforcement."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_prompt(resume_text, missing_skills) + groq_json_instructions(_GROQ_RESUME_FIELDS_SPEC)

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        # Matches the token budget used for the equivalent Gemini call.
        max_tokens=6000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    for key in _RESUME_FIELD_KEYS:
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
    current_draft: dict,
    jd_content: str | None = None,
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
        resume_text, missing_skills, current_draft, jd_content
    ) + groq_json_instructions('"reply" (string), plus ' + _GROQ_RESUME_FIELDS_SPEC)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": "assistant" if m["role"] == "assistant" else "user", "content": m["content"]} for m in conversation
    )
    if not conversation:
        messages.append({"role": "user", "content": "Please begin."})

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=6000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    for key in ["reply"] + _RESUME_FIELD_KEYS:
        if key not in result:
            raise ValueError(f"Groq response missing required key: {key}")
    result["source"] = "ai"
    return result


def _try_groq_chat(
    conversation: list[dict],
    resume_text: str,
    missing_skills: list[str],
    current_draft: dict,
    jd_content: str | None = None,
) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing deterministic fallback instead of surfacing an error."""
    try:
        result = _chat_via_groq(conversation, resume_text, missing_skills, current_draft, jd_content)
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


def _build_prompt(resume_text: str, missing_skills: list[str]) -> str:
    prompt = (
        "You are an expert resume writer producing a complete, professionally structured resume — "
        "the kind with a clear headline, a tight summary, a skills line, one clearly separated entry "
        "per job (title, company, dates, quantified bullets), an education section, and a "
        "certifications section — using ONLY the experience and facts already present in the resume "
        "text below.\n\n"
        "Do the following:\n"
        "1. Write a short professional headline/title (e.g. \"Senior Backend Engineer\" or "
        "\"Marketing & Sales Professional\") that reflects their most recent or strongest role.\n"
        "2. Rewrite the professional summary to be sharper and more compelling (2-4 sentences).\n"
        "3. Produce a flat list of individual skills (not grouped into categories, not one long "
        "sentence) — each entry should be a single skill name, ready to display as a bullet-separated "
        "line.\n"
        "4. Extract EVERY job found in the resume as its own structured entry: job title, company "
        "name, start date, end date (use \"Present\" if it's their current role), and up to 5 "
        "rewritten, quantified bullet points per job (use metrics/numbers only if they are already "
        "implied or present in the original text — do not invent statistics). Preserve the resume's "
        "own chronological order.\n"
        "5. Extract every education entry found (degree, school/institution, graduation date or "
        "expected date). Return an empty list if the resume genuinely has none — never invent one.\n"
        "6. Extract every certification/license mentioned. Return an empty list if there are none — "
        "never invent one.\n\n"
        "CRITICAL RULE: Never fabricate skills, credentials, employers, job titles, dates, degrees, "
        "schools, or accomplishments the person does not plausibly have. Do not claim experience with "
        "a technology unless the resume already shows evidence of related, transferable experience. "
        "If a section (education, certifications) has no basis anywhere in the resume text, return it "
        "as an empty list rather than guessing.\n\n"
        f"Resume:\n{resume_text[:6000]}"
    )

    if missing_skills:
        skills_list = ", ".join(missing_skills)
        prompt += (
            f"\n\nThe following skills were identified as missing when this resume was matched against "
            f"a target job: {skills_list}. If — and only if — the resume shows genuinely related or "
            "transferable experience for any of these skills, you may naturally incorporate that skill "
            "into the skills list or an experience bullet, phrased honestly (e.g. 'exposure to', "
            "'familiarity with') rather than claiming deep expertise. Do NOT add a skill if there is no "
            "plausible basis for it anywhere in the resume — it is far better to omit a missing skill "
            "than to fabricate a claim."
        )

    return prompt


def generate_enhanced_resume(resume_text: str, missing_skills: list[str], fallback_data: dict, ai_enabled: bool = True) -> dict:
    """Call Gemini to produce a complete structured resume (headline, summary, skills, per-job
    experience entries, education, certifications) from the candidate's resume text. Falls back to
    a deterministic, lightly-reformatted version of the original content if the API key is missing,
    AI features have been disabled platform-wide (ai_enabled=False, set via Admin Settings), or the
    call fails. Uses the free-tier Gemini API (server-wide GEMINI_API_KEY env var) rather than a
    per-user key."""
    if not ai_enabled:
        return _fallback_response("AI resume building has been disabled by the administrator.", fallback_data)

    gemini_keys = _gemini_api_keys()
    if not gemini_keys:
        return _fallback_response("AI resume building is not configured (no API key set).", fallback_data)

    last_quota_error = None
    for api_key in gemini_keys:
        try:
            client = _client(api_key)
            response = client.models.generate_content(
                model=MODEL,
                contents=_build_prompt(resume_text, missing_skills),
                config=genai_types.GenerateContentConfig(
                    # Raised from 2048/6000 in earlier revisions of this schema — a full
                    # per-job-structured resume (several jobs, each with its own bullets)
                    # needs materially more output tokens than the old flat-bullets shape.
                    max_output_tokens=8000,
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
                last_quota_error = e
                continue  # try the next configured Gemini key, if any
            return _fallback_response("The AI service returned an error. Showing your original content instead.", fallback_data)
        except genai_errors.ServerError:
            return _fallback_response("Could not reach the AI service. Showing your original content instead.", fallback_data)
        except Exception:
            return _fallback_response("AI resume building is temporarily unavailable. Showing your original content instead.", fallback_data)

    # Every configured Gemini key hit a 429 — try Groq before giving up.
    groq_result = _try_groq_generate(resume_text, missing_skills)
    if groq_result is not None:
        return groq_result
    if last_quota_error is not None and _is_daily_quota_error(last_quota_error):
        return _fallback_response(
            "AI resume building has hit its daily usage limit — it'll be back once that resets, or "
            "once an admin upgrades the AI plan. Showing your original content instead.",
            fallback_data,
        )
    return _fallback_response("AI resume building is temporarily rate-limited. Showing your original content instead.", fallback_data)


def _draft_state_text(current_draft: dict) -> str:
    experience = current_draft.get("experience") or []
    education = current_draft.get("education") or []
    certifications = current_draft.get("certifications") or []
    skills = current_draft.get("skills") or []

    experience_text = "\n".join(
        f"- {job.get('title', '')} at {job.get('company', '')} "
        f"({job.get('start_date', '')} - {job.get('end_date', '')}): "
        + "; ".join(job.get("bullets") or [])
        for job in experience
    ) or "(none)"
    education_text = "\n".join(
        f"- {edu.get('degree', '')}, {edu.get('school', '')} ({edu.get('date', '')})" for edu in education
    ) or "(none)"

    return (
        f"Title: {current_draft.get('title', '')}\n"
        f"Summary: {current_draft.get('summary', '')}\n"
        f"Skills: {', '.join(skills) if skills else '(none)'}\n"
        f"Experience:\n{experience_text}\n"
        f"Education:\n{education_text}\n"
        f"Certifications: {', '.join(certifications) if certifications else '(none)'}"
    )


def _build_chat_system_prompt(
    resume_text: str,
    missing_skills: list[str],
    current_draft: dict,
    jd_content: str | None = None,
) -> str:
    skills_list = ", ".join(missing_skills) if missing_skills else "none noted"
    has_draft = bool(
        current_draft.get("summary") or current_draft.get("experience") or current_draft.get("skills")
        or current_draft.get("education") or current_draft.get("certifications")
    )

    if resume_text:
        grounding = (
            f"The user has a saved resume you can draw on (they may also give you new information "
            f"directly in chat — combine both):\n{resume_text[:4000]}"
        )
    else:
        grounding = (
            "The user hasn't uploaded or saved a resume yet. Build their resume from what they tell you "
            "in this conversation instead — ask about their target role, work history (job titles, "
            "companies, dates), education, and skills if you don't have enough yet. They can also upload "
            "an existing CV at any point using the upload control, which becomes your grounding source "
            "from then on."
        )

    draft_state = _draft_state_text(current_draft) if has_draft else "(nothing drafted yet)"

    jd_block = (
        f"\n\nTarget job description the user wants this resume tailored to match (they extracted this from a "
        f"job posting link, or pasted it in) — prioritize the skills, keywords, and requirements it asks for "
        f"whenever you write or revise the draft, without fabricating anything the user's real background "
        f"doesn't support:\n{jd_content[:3000]}"
        if jd_content
        else ""
    )

    return (
        "You are an expert, proactive AI resume-building assistant and career coach — the kind of "
        "conversational assistant users expect from a modern AI chat assistant, not a rigid form "
        "that only executes literal commands. You're having an ongoing conversation with the user to help "
        "them build a complete, professionally structured resume: a headline, a summary, a skills list, "
        "one clearly separated entry per job (title, company, dates, bullets), an education section, and "
        "a certifications section.\n\n"
        f"{grounding}\n\n"
        f"Skills identified as missing against a target job (if any): {skills_list}\n\n"
        f"Current draft of the resume you're building/editing together:\n{draft_state}"
        f"{jd_block}\n\n"
        "How to behave:\n"
        "- Be proactive, not passive. Don't just wait for exact instructions — drive the conversation "
        "forward. If the user says something vague like \"help me build my resume\" or \"improve my CV\", "
        "don't ask them to be more specific — immediately start gathering what you need by asking a "
        "focused question (e.g. their target role, most recent job, or which section to start with).\n"
        "- Ask one or two focused follow-up questions at a time, not a long checklist — this is a "
        "conversation, not an intake form. Once you have enough for one section (e.g. one job's title, "
        "company, and dates), use it, then move to the next gap.\n"
        "- Actively identify what's missing or weak — no quantified impact, a thin skills list, a "
        "generic summary, a job with no dates, no education/certifications section at all — and say so, "
        "either suggesting a concrete fix or asking for the specific detail you need to fix it, rather "
        "than staying silent about it.\n"
        "- When you write or revise a bullet or summary, briefly note WHY it's stronger (e.g. \"added a "
        "metric\", \"led with the impact\") so the user learns from it, not just receives output.\n"
        "- Offer career judgment when it's relevant: if their target role doesn't match their strongest "
        "experience, say so; suggest which experience to lead with, which skills to foreground, or how to "
        "frame a career change — but only using what you actually know about them from this conversation "
        "or their resume.\n"
        "- Apply explicit edit requests (add/remove/change something) to the CURRENT DRAFT above, "
        "building on it incrementally, exactly as asked.\n\n"
        "Ground rules (never break these):\n"
        "- Never fabricate skills, credentials, employers, job titles, dates, degrees, schools, or "
        "accomplishments — only include what the user has told you (via a saved resume or this "
        "conversation) or what's plausibly implied by it.\n"
        "- If you don't yet have enough real information for a job's title/company/dates, or for an "
        "education/certification entry, don't invent placeholder content — ask the user for the details "
        "instead, and leave that entry out of the draft until you have it.\n"
        "- Keep replies conversational and focused — typically 2-6 sentences; longer only when you're "
        "listing specific suggestions or a couple of questions worth asking together.\n"
        "- Always return the FULL current state of the resume (title, summary, all skills, all "
        "experience entries, all education entries, all certifications) in the structured fields, "
        "reflecting any changes from this turn — even fields you didn't touch. Contact info (name, "
        "email, phone, location) is handled separately by the platform — never ask the user for it or "
        "include it in your reply."
    )


def chat_about_resume(
    conversation: list[dict],
    resume_text: str,
    missing_skills: list[str],
    current_draft: dict,
    ai_enabled: bool = True,
    jd_content: str | None = None,
) -> dict:
    """One turn of AI-assisted, conversational resume editing. conversation is a list of
    {"role": "user"|"assistant", "content": str} in chronological order, not including the reply
    being generated now. current_draft holds whatever the frontend currently has for
    title/summary/skills/experience/education/certifications (any/all may be empty). Uses the
    free-tier Gemini API (server-wide GEMINI_API_KEY env var). Resume chat editing has no
    rule-based equivalent, so if AI is disabled/unavailable the draft is returned unchanged with an
    explanatory reply rather than a fabricated edit."""
    def _unchanged_draft() -> dict:
        return {key: current_draft.get(key, [] if key != "title" and key != "summary" else "") for key in _RESUME_FIELD_KEYS}

    unavailable_reply = {
        "reply": (
            "AI resume chat isn't available right now — the AI service isn't configured. You can still "
            "use the one-shot Generate button, or edit the text directly."
        ),
        **_unchanged_draft(),
        "source": "fallback",
    }

    if not ai_enabled:
        unavailable_reply["reply"] = "AI resume chat has been disabled by the administrator."
        logger.info("resume_builder.chat_about_resume served by fallback (AI disabled by admin)")
        return unavailable_reply

    gemini_keys = _gemini_api_keys()
    if not gemini_keys:
        logger.info("resume_builder.chat_about_resume served by fallback (no GEMINI_API_KEY configured)")
        return unavailable_reply

    last_quota_error = None
    for api_key in gemini_keys:
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
                    max_output_tokens=8000,
                    thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                    system_instruction=_build_chat_system_prompt(
                        resume_text, missing_skills, current_draft, jd_content,
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
                last_quota_error = e
                continue  # try the next configured Gemini key, if any

            error_reply = dict(unavailable_reply)
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

    # Every configured Gemini key hit a 429 — try Groq before giving up.
    groq_result = _try_groq_chat(conversation, resume_text, missing_skills, current_draft, jd_content)
    if groq_result is not None:
        return groq_result

    error_reply = dict(unavailable_reply)
    error_reply["reply"] = (
        "The AI assistant has hit its daily usage limit — it'll be back once that resets, or once an "
        "admin upgrades the AI plan. Your draft wasn't changed; you can still edit it directly."
        if last_quota_error is not None and _is_daily_quota_error(last_quota_error)
        else "You're sending messages a bit fast — give it a moment and try again."
    )
    logger.info("resume_builder.chat_about_resume served by fallback (all gemini keys quota/rate-limited)")
    return error_reply


def _split_lines(text: str, limit: int | None = None) -> list[str]:
    lines = [line.strip(" -•\t") for line in (text or "").split("\n") if line.strip()]
    return lines[:limit] if limit else lines


def _fallback_response(message: str, fallback_data: dict) -> dict:
    """Deterministic, non-AI resume structuring — reuses whatever
    resume_structurer.py already parsed out of the original file (summary,
    experience, education, certifications, skills) rather than inventing
    anything. Experience can't be reliably split into distinct per-job
    title/company/dates without AI, so it's returned as a single entry
    holding the original text as bullets — genuinely less structured than
    the AI path, but never fabricated."""
    logger.info("resume_builder.generate_enhanced_resume served by fallback (%s)", message)
    original_summary = (fallback_data.get("original_summary") or "").strip()
    original_experience = (fallback_data.get("original_experience") or "").strip()
    original_education = (fallback_data.get("original_education") or "").strip()
    original_certifications = (fallback_data.get("original_certifications") or "").strip()
    original_skills = fallback_data.get("original_skills") or []
    original_title = (fallback_data.get("original_title") or "").strip()

    summary = original_summary if original_summary else "No professional summary was found on your resume."

    experience = []
    if original_experience:
        experience = [{
            "title": "", "company": "", "start_date": "", "end_date": "",
            "bullets": _split_lines(original_experience, limit=8),
        }]

    return {
        "title": original_title or "Professional",
        "summary": summary,
        "skills": original_skills,
        "experience": experience,
        "education": [{"degree": line, "school": "", "date": ""} for line in _split_lines(original_education)],
        "certifications": _split_lines(original_certifications),
        "overall_assessment": message,
        "source": "fallback",
    }
