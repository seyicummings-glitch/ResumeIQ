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
# Output shape — a real, professionally structured, recruiter/ATS-standard
# resume: headline, a tight 3-5 sentence summary, skills split into
# technical/soft, one entry per job with its own title/company/dates/
# achievement-focused bullets, education, certifications, projects (with
# technologies used), and languages. Contact info (name, email, phone,
# LinkedIn, location, portfolio) is deliberately NOT part of this schema —
# it's never AI-generated; app/routes/resume_builder.py fills it in straight
# from the user's own profile fields, which is both more reliable and
# structurally prevents the AI from ever inventing someone's contact
# details. References work the same way in spirit: the AI only ever echoes
# references the source resume genuinely lists, never invents names or
# contacts for that section.
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

_SKILLS_SCHEMA = {
    "type": "object",
    "properties": {
        "technical": {"type": "array", "items": {"type": "string"}},
        "soft": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["technical", "soft"],
    "additionalProperties": False,
}

_PROJECT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "technologies": {"type": "array", "items": {"type": "string"}},
        # Results-focused bullets — "Results Achieved", not a task list.
        "bullets": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "description", "technologies", "bullets"],
    "additionalProperties": False,
}

_LANGUAGE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "proficiency": {"type": "string"},
    },
    "required": ["name", "proficiency"],
    "additionalProperties": False,
}

_RESUME_FIELDS = {
    "title": {"type": "string"},
    "summary": {"type": "string"},
    "skills": _SKILLS_SCHEMA,
    "experience": {"type": "array", "items": _EXPERIENCE_ITEM_SCHEMA},
    "education": {"type": "array", "items": _EDUCATION_ITEM_SCHEMA},
    "certifications": {"type": "array", "items": {"type": "string"}},
    "projects": {"type": "array", "items": _PROJECT_ITEM_SCHEMA},
    "languages": {"type": "array", "items": _LANGUAGE_ITEM_SCHEMA},
    "references": {"type": "array", "items": {"type": "string"}},
}
_RESUME_FIELD_KEYS = list(_RESUME_FIELDS.keys())
_EMPTY_SKILLS = {"technical": [], "soft": []}
_RESUME_FIELD_DEFAULTS = {
    "title": "", "summary": "", "skills": dict(_EMPTY_SKILLS), "experience": [], "education": [],
    "certifications": [], "projects": [], "languages": [], "references": [],
}

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
    '"summary" (string — exactly 3-5 recruiter-style sentences), '
    '"skills" (an OBJECT — not an array — with "technical" (array of strings: hard skills, tools, '
    'technologies, domain competencies) and "soft" (array of strings: communication, leadership, '
    'teamwork, and similar interpersonal skills) — categorize every skill into the correct bucket), '
    '"experience" (array of objects, one per job, each with "title" (string), "company" (string), '
    '"start_date" (string), "end_date" (string, "Present" if current), "bullets" (array of strings — '
    'each an achievement-focused, quantified, action-verb-led accomplishment, never a bare task)), '
    '"education" (array of objects, each with "degree" (string), "school" (string), "date" (string)), '
    '"certifications" (array of strings — relevant ones only), '
    '"projects" (array of objects, each with "name" (string), "description" (string, one sentence), '
    '"technologies" (array of strings — tools/tech used), "bullets" (array of strings — results '
    'achieved) — empty array if the resume describes no projects), '
    '"languages" (array of objects, each with "name" (string) and "proficiency" (string, e.g. '
    '"Fluent", "Native", "Conversational") — empty array unless languages are explicitly stated), '
    '"references" (array of strings — empty array unless the source resume explicitly lists named '
    'references; never invent one)'
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


def _generate_via_groq(resume_text: str, missing_skills: list[str], target_role: str = "", industry: str = "") -> dict:
    """Groq equivalent of the Gemini call in generate_enhanced_resume — same
    prompt/grounding/anti-fabrication rules (reuses _build_prompt exactly),
    adapted only in how the JSON shape is requested and parsed, since Groq's
    OpenAI-compatible API has JSON *mode* but not Gemini's strict
    response_json_schema enforcement."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_prompt(resume_text, missing_skills, target_role, industry) + groq_json_instructions(_GROQ_RESUME_FIELDS_SPEC)

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        # Matches the token budget used for the equivalent Gemini call.
        max_tokens=10000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    for key in _RESUME_FIELD_KEYS:
        if key not in result:
            raise ValueError(f"Groq response missing required key: {key}")
    result["source"] = "ai"
    return result


def _try_groq_generate(resume_text: str, missing_skills: list[str], target_role: str = "", industry: str = "") -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing deterministic fallback instead of surfacing an error."""
    try:
        result = _generate_via_groq(resume_text, missing_skills, target_role, industry)
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
    target_role: str = "",
    industry: str = "",
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
        resume_text, missing_skills, current_draft, jd_content, target_role, industry
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
        max_tokens=10000,
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
    target_role: str = "",
    industry: str = "",
) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing deterministic fallback instead of surfacing an error."""
    try:
        result = _chat_via_groq(conversation, resume_text, missing_skills, current_draft, jd_content, target_role, industry)
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


def _role_context_block(target_role: str = "", industry: str = "") -> str:
    """Keeps every generated skill/keyword/suggestion consistent with the candidate's own field —
    e.g. never lets a marketing resume pick up software-engineering skills, or vice versa. This is
    strictly a coherence/emphasis instruction, not license to invent: the anti-fabrication rule
    below still applies in full."""
    role_focus = " / ".join(filter(None, [target_role, industry]))
    if not role_focus:
        return ""
    return (
        f"\n\nThe candidate's target role/industry is: {role_focus}. Generate and phrase content "
        f"appropriate to THIS field specifically (e.g. marketing skills/achievements for a marketing "
        f"candidate, technical skills/achievements for a software engineering candidate, sales metrics "
        f"for a sales candidate, business-operations content for a business administration candidate). "
        "Never introduce skills, keywords, or achievements from an unrelated field — use the target "
        "role only to decide what to emphasize and how to phrase it, never as license to invent "
        "experience the resume doesn't already show."
    )


def _build_prompt(resume_text: str, missing_skills: list[str], target_role: str = "", industry: str = "") -> str:
    prompt = (
        "You are a senior professional resume writer and recruiter producing a resume that meets real "
        "recruiter and ATS (Applicant Tracking System) standards — the kind written by an experienced "
        "recruiter, not a chatbot reply. Use ONLY the experience and facts already present in the "
        "resume text below; never invent anything, but rewrite and sharpen everything you do use. Never "
        "write any section as a wall of prose — every section must be scannable, structured content.\n\n"
        "Do the following:\n"
        "1. Write a short professional headline/title (e.g. \"Senior Backend Engineer\" or "
        "\"Marketing & Sales Professional\") that reflects their most recent or strongest role.\n"
        "2. Write the PROFESSIONAL SUMMARY as exactly 3-5 sentences — recruiter-style, focused on years "
        "of experience, standout achievements, core strengths, and the candidate's value proposition. "
        "No filler, no generic claims (\"hard-working team player\") that could describe anyone — every "
        "sentence must say something specific to this candidate. Keep it a separate section; never merge "
        "it with contact information.\n"
        "3. Produce a skills list organized into two clean groups: \"technical\" (hard skills, tools, "
        "technologies, domain competencies — e.g. \"Project Management\", \"CRM Systems\", \"Budget "
        "Planning\", \"Data Analysis\") and \"soft\" (interpersonal/workplace skills — e.g. "
        "\"Communication\", \"Leadership\", \"Problem Solving\"). Use real, ATS-relevant keywords the "
        "candidate's own background genuinely supports — never keyword-stuff with terms unrelated to "
        "their field.\n"
        "4. Extract EVERY job found in the resume as its own structured entry: job title, company name, "
        "start date, end date (use \"Present\" if it's their current role), and up to 5 "
        "achievement-focused bullet points per job. Every bullet must:\n"
        "   - Start with a strong action verb (Led, Managed, Built, Increased, Delivered, Negotiated, "
        "Launched...)\n"
        "   - State a measurable result wherever the original text supports one (%, $, time saved, "
        "volume, headcount, scale) — never invent a number that isn't implied by the source text\n"
        "   - Describe business impact and outcome, not just the task that was performed\n"
        "   Bad: \"Responsible for marketing campaigns.\"\n"
        "   Good: \"Led digital marketing campaigns that increased qualified leads by 45%.\"\n"
        "   Bad: \"Responsible for client accounts.\"\n"
        "   Good: \"Managed a portfolio worth $1.2M in annual revenue, improving client retention by "
        "20%.\"\n"
        "   Rewrite any task-based, passive description (\"Responsible for...\", \"Duties included...\") "
        "into this achievement-focused style using only what the original text actually supports — if "
        "no metric is genuinely available, still lead with the outcome/impact rather than the bare "
        "task. Preserve the resume's own chronological order. Never write experience as a paragraph.\n"
        "5. Extract every education entry found (degree, school/institution, graduation date or "
        "expected date). Return an empty list if the resume genuinely has none — never invent one.\n"
        "6. Extract certifications/licenses that are genuinely relevant to the candidate's field. Never "
        "invent one; don't omit a real, relevant certification either.\n"
        "7. Extract every project described (personal, academic, or side projects — not the jobs "
        "already captured in experience): a short name, a one-sentence description, the "
        "technologies/tools actually used, and up to 4 results-focused bullets (impact/outcomes "
        "achieved, in the same achievement-focused style as work experience — not a task list). Return "
        "an empty list if the resume describes no projects — never invent one.\n"
        "8. Extract languages ONLY if the resume explicitly states them, each with a proficiency level "
        "(\"Native\", \"Fluent\", \"Conversational\", \"Basic\", or whatever the resume itself says). "
        "Return an empty list if none are stated — never assume someone speaks a language.\n"
        "9. References: return an empty list unless the resume text itself already lists named "
        "references with their own contact details — never invent names, titles, or contact info for "
        "this section, and never add boilerplate like \"available upon request\" unless that literal "
        "text already appears on the resume.\n\n"
        "Writing quality bar (apply throughout every section):\n"
        "- Rewrite weak or vague content into something concrete and specific.\n"
        "- Fix grammar and awkward phrasing.\n"
        "- Use precise, industry-appropriate, ATS-friendly keywords the candidate's real background "
        "supports.\n"
        "- Avoid generic filler statements, repetitive phrasing across bullets, and keyword stuffing.\n\n"
        "CRITICAL RULE: Never fabricate skills, credentials, employers, job titles, dates, degrees, "
        "schools, projects, languages, references, metrics, or accomplishments the person does not "
        "plausibly have. Do not claim experience with a technology unless the resume already shows "
        "evidence of related, transferable experience. If a section has no basis anywhere in the resume "
        "text, return it as an empty list rather than guessing."
        f"{_role_context_block(target_role, industry)}\n\n"
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
    """Call Gemini to produce a complete, recruiter/ATS-standard structured resume (headline, a
    3-5 sentence summary, categorized skills, per-job achievement-focused experience entries,
    education, relevant certifications, projects with technologies/results, languages) from the
    candidate's resume text. Falls back to a deterministic, lightly-reformatted version of the
    original content if the API key is missing, AI features have been disabled platform-wide
    (ai_enabled=False, set via Admin Settings), or the call fails. Uses the free-tier Gemini API
    (server-wide GEMINI_API_KEY env var) rather than a per-user key.

    fallback_data may include "target_role" and "target_industry" (the user's own profile fields)
    — used only to keep generated content coherent with the candidate's actual field (e.g. never
    surfacing software-engineering skills on a marketing resume), never as license to invent
    experience."""
    target_role = fallback_data.get("target_role") or fallback_data.get("original_title") or ""
    industry = fallback_data.get("target_industry") or ""

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
                contents=_build_prompt(resume_text, missing_skills, target_role, industry),
                config=genai_types.GenerateContentConfig(
                    # A full per-job-structured resume with categorized skills, projects, and
                    # languages needs materially more output tokens than a flat-bullets shape.
                    max_output_tokens=10000,
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
    groq_result = _try_groq_generate(resume_text, missing_skills, target_role, industry)
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
    skills = current_draft.get("skills") or {}
    technical_skills = skills.get("technical") or []
    soft_skills = skills.get("soft") or []
    projects = current_draft.get("projects") or []
    languages = current_draft.get("languages") or []
    references = current_draft.get("references") or []

    experience_text = "\n".join(
        f"- {job.get('title', '')} at {job.get('company', '')} "
        f"({job.get('start_date', '')} - {job.get('end_date', '')}): "
        + "; ".join(job.get("bullets") or [])
        for job in experience
    ) or "(none)"
    education_text = "\n".join(
        f"- {edu.get('degree', '')}, {edu.get('school', '')} ({edu.get('date', '')})" for edu in education
    ) or "(none)"
    projects_text = "\n".join(
        f"- {proj.get('name', '')} [{', '.join(proj.get('technologies') or [])}]: {proj.get('description', '')} "
        + "; ".join(proj.get("bullets") or [])
        for proj in projects
    ) or "(none)"
    languages_text = ", ".join(
        f"{lang.get('name', '')} ({lang.get('proficiency', '')})" for lang in languages
    ) or "(none)"

    return (
        f"Title: {current_draft.get('title', '')}\n"
        f"Summary: {current_draft.get('summary', '')}\n"
        f"Technical skills: {', '.join(technical_skills) if technical_skills else '(none)'}\n"
        f"Soft skills: {', '.join(soft_skills) if soft_skills else '(none)'}\n"
        f"Experience:\n{experience_text}\n"
        f"Education:\n{education_text}\n"
        f"Certifications: {', '.join(certifications) if certifications else '(none)'}\n"
        f"Projects:\n{projects_text}\n"
        f"Languages: {languages_text}\n"
        f"References: {', '.join(references) if references else '(none)'}"
    )


def _build_chat_system_prompt(
    resume_text: str,
    missing_skills: list[str],
    current_draft: dict,
    jd_content: str | None = None,
    target_role: str = "",
    industry: str = "",
) -> str:
    skills_list = ", ".join(missing_skills) if missing_skills else "none noted"
    draft_skills = current_draft.get("skills") or {}
    has_skills = bool(draft_skills.get("technical") or draft_skills.get("soft"))
    has_draft = bool(
        current_draft.get("summary") or current_draft.get("experience") or has_skills
        or current_draft.get("education") or current_draft.get("certifications")
        or current_draft.get("projects") or current_draft.get("languages") or current_draft.get("references")
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
        "You are an expert, proactive AI resume-building assistant, senior resume writer, and career "
        "coach — the kind of conversational assistant users expect from a modern AI chat assistant, not "
        "a rigid form that only executes literal commands, and the kind of resume writer who meets real "
        "recruiter and ATS standards. You're having an ongoing conversation with the user to help them "
        "build a complete, professionally structured resume: a headline, a 3-5 sentence summary, skills "
        "split into technical and soft, one clearly separated entry per job (title, company, dates, "
        "achievement-focused bullets), an education section, a certifications section, a projects "
        "section (with technologies used and results achieved), and a languages section.\n\n"
        f"{grounding}\n\n"
        f"Skills identified as missing against a target job (if any): {skills_list}\n\n"
        f"Current draft of the resume you're building/editing together:\n{draft_state}"
        f"{jd_block}"
        f"{_role_context_block(target_role, industry)}\n\n"
        "How to behave:\n"
        "- Be proactive, not passive. Don't just wait for exact instructions — drive the conversation "
        "forward. If the user says something vague like \"help me build my resume\" or \"improve my CV\", "
        "don't ask them to be more specific — immediately start gathering what you need by asking a "
        "focused question (e.g. their target role, most recent job, or which section to start with).\n"
        "- Ask one or two focused follow-up questions at a time, not a long checklist — this is a "
        "conversation, not an intake form. Once you have enough for one section (e.g. one job's title, "
        "company, and dates), use it, then move to the next gap.\n"
        "- Actively identify what's missing or weak — a task-based bullet with no measurable impact, a "
        "thin skills list, a generic summary sentence that could describe anyone, a job with no dates, "
        "no education/certifications section at all — and say so, either suggesting a concrete fix or "
        "asking for the specific detail you need to fix it, rather than staying silent about it.\n"
        "- When you write or revise a bullet or summary, briefly note WHY it's stronger (e.g. \"added a "
        "metric\", \"led with the business impact instead of the task\") so the user learns from it, not "
        "just receives output.\n"
        "- Offer career judgment when it's relevant: if their target role doesn't match their strongest "
        "experience, say so; suggest which experience to lead with, which skills to foreground, or how to "
        "frame a career change — but only using what you actually know about them from this conversation "
        "or their resume.\n"
        "- Apply explicit edit requests (add/remove/change something) to the CURRENT DRAFT above, "
        "building on it incrementally, exactly as asked.\n\n"
        "Writing quality bar (apply whenever you write or revise anything):\n"
        "- Every experience and project bullet starts with a strong action verb, states a measurable "
        "result wherever the source material supports one (%, $, time, volume, scale), and describes "
        "business impact — never a bare task description. Bad: \"Responsible for marketing campaigns.\" "
        "Good: \"Led digital marketing campaigns that increased qualified leads by 45%.\"\n"
        "- The summary is exactly 3-5 sentences, specific to this candidate — no generic filler that "
        "could describe anyone.\n"
        "- Fix grammar and awkward phrasing; use precise, ATS-friendly keywords the candidate's real "
        "background supports; avoid repetitive phrasing across bullets and avoid keyword stuffing.\n\n"
        "Ground rules (never break these):\n"
        "- Never fabricate skills, credentials, employers, job titles, dates, degrees, schools, "
        "projects, languages, references, metrics, or accomplishments — only include what the user has "
        "told you (via a saved resume or this conversation) or what's plausibly implied by it.\n"
        "- If you don't yet have enough real information for a job's title/company/dates, or for an "
        "education/certification/project entry, don't invent placeholder content — ask the user for the "
        "details instead, and leave that entry out of the draft until you have it.\n"
        "- Only include a language if the user or their resume explicitly states they speak it, and "
        "only include a reference if the user or their resume explicitly provides one — never add "
        "placeholder or boilerplate content for either.\n"
        "- Categorize every skill honestly into technical vs. soft — don't dump everything into one "
        "bucket.\n"
        "- Keep replies conversational and focused — typically 2-6 sentences; longer only when you're "
        "listing specific suggestions or a couple of questions worth asking together.\n"
        "- Always return the FULL current state of the resume (title, summary, all skills in both "
        "buckets, all experience entries, all education entries, all certifications, all projects, all "
        "languages, all references) in the structured fields, reflecting any changes from this turn — "
        "even fields you didn't touch. Contact info (name, email, phone, location, LinkedIn, portfolio) "
        "is handled separately by the platform — never ask the user for it or include it in your reply."
    )


def chat_about_resume(
    conversation: list[dict],
    resume_text: str,
    missing_skills: list[str],
    current_draft: dict,
    ai_enabled: bool = True,
    jd_content: str | None = None,
    target_role: str | None = None,
    industry: str | None = None,
) -> dict:
    """One turn of AI-assisted, conversational resume editing. conversation is a list of
    {"role": "user"|"assistant", "content": str} in chronological order, not including the reply
    being generated now. current_draft holds whatever the frontend currently has for
    title/summary/skills/experience/education/certifications/projects/languages/references (any/all
    may be empty). target_role/industry (the user's own profile fields) are used only to keep
    generated content coherent with the candidate's actual field, never as license to invent
    experience. Uses the free-tier Gemini API (server-wide GEMINI_API_KEY env var). Resume chat
    editing has no rule-based equivalent, so if AI is disabled/unavailable the draft is returned
    unchanged with an explanatory reply rather than a fabricated edit."""
    target_role = target_role or ""
    industry = industry or ""

    def _unchanged_draft() -> dict:
        return {key: current_draft.get(key, _RESUME_FIELD_DEFAULTS[key]) for key in _RESUME_FIELD_KEYS}

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
                    max_output_tokens=10000,
                    thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                    system_instruction=_build_chat_system_prompt(
                        resume_text, missing_skills, current_draft, jd_content, target_role, industry,
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
    groq_result = _try_groq_chat(conversation, resume_text, missing_skills, current_draft, jd_content, target_role, industry)
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


# Best-effort keyword set for categorizing a flat skills list into technical vs. soft when no AI is
# available to judge it properly — anything not recognized as a soft skill is treated as technical,
# since the original data on this deterministic path is far more often tools/technologies than not.
_SOFT_SKILL_KEYWORDS = {
    "communication", "leadership", "teamwork", "team work", "collaboration", "problem solving",
    "problem-solving", "critical thinking", "adaptability", "time management", "creativity",
    "work ethic", "interpersonal skills", "conflict resolution", "decision making", "decision-making",
    "emotional intelligence", "negotiation", "public speaking", "presentation skills", "mentoring",
    "coaching", "attention to detail", "organization", "organizational skills", "flexibility",
    "empathy", "active listening", "customer service", "multitasking", "self-motivation",
    "accountability", "strategic thinking", "delegation", "reliability", "patience",
}


def _categorize_skills(skills: list[str]) -> dict:
    technical, soft = [], []
    for skill in skills:
        (soft if skill.strip().lower() in _SOFT_SKILL_KEYWORDS else technical).append(skill)
    return {"technical": technical, "soft": soft}


def _fallback_response(message: str, fallback_data: dict) -> dict:
    """Deterministic, non-AI resume structuring — reuses whatever
    resume_structurer.py already parsed out of the original file (summary,
    experience, education, certifications, skills, projects) rather than
    inventing anything. Experience can't be reliably split into distinct
    per-job title/company/dates without AI, so it's returned as a single
    entry holding the original text as bullets — genuinely less structured
    than the AI path, but never fabricated. Languages and references have no
    reliable non-AI source, so they're always empty on this path."""
    logger.info("resume_builder.generate_enhanced_resume served by fallback (%s)", message)
    original_summary = (fallback_data.get("original_summary") or "").strip()
    original_experience = (fallback_data.get("original_experience") or "").strip()
    original_education = (fallback_data.get("original_education") or "").strip()
    original_certifications = (fallback_data.get("original_certifications") or "").strip()
    original_projects = (fallback_data.get("original_projects") or "").strip()
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
        "skills": _categorize_skills(original_skills),
        "experience": experience,
        "education": [{"degree": line, "school": "", "date": ""} for line in _split_lines(original_education)],
        "certifications": _split_lines(original_certifications),
        "projects": [
            {"name": line, "description": "", "technologies": [], "bullets": []}
            for line in _split_lines(original_projects)
        ],
        "languages": [],
        "references": [],
        "overall_assessment": message,
        "source": "fallback",
    }
