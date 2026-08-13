"""
AI-generated learning roadmap. Follows the same shape as the rest of this
app's AI services (ai_interviewer.py, skill_assessment_ai.py): Gemini SDK, a
GEMINI_API_KEY gate, structured JSON output, and a caller-side fallback (see
app/services/learning_roadmap.py) when AI is disabled or unavailable.

The roadmap is NOT built from the resume alone — the candidate's chosen
target_role and industry are given highest priority in the prompt, so the
plan covers what the role actually requires even for technologies the CV
never mentions. The resume, job description, detected skill gaps, latest
skill-assessment results, and latest interview feedback are all folded in as
supporting context.
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


def _gemini_api_keys() -> list[str]:
    """A second Gemini key (GEMINI_API_KEY_2, e.g. from a different Google
    account) is optional extra daily quota tried before falling through to
    Groq — most installs will only have the first key set, in which case this
    behaves exactly as if there were only ever one."""
    return [k for k in [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")] if k]


STAGE_NAMES = ["Foundation", "Intermediate", "Advanced", "Job Ready"]
TOPICS_PER_STAGE = 4

_MILESTONES_SCHEMA = {
    "type": "object",
    "properties": {
        "beginner": {"type": "string"},
        "intermediate": {"type": "string"},
        "advanced": {"type": "string"},
    },
    "required": ["beginner", "intermediate", "advanced"],
    "additionalProperties": False,
}

_QUIZ_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
        "correct_index": {"type": "integer"},
        "explanation": {"type": "string"},
    },
    "required": ["question", "options", "correct_index", "explanation"],
    "additionalProperties": False,
}

_TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "category": {"type": "string"},
        "why_it_matters": {"type": "string"},
        "current_gap": {"type": "string"},
        "learning_objectives": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
        "milestones": _MILESTONES_SCHEMA,
        "resources": {
            "type": "array",
            "minItems": 2,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["Course", "Free", "Book", "Docs", "Cert", "Video", "Article", "Tutorial"],
                    },
                    "provider": {"type": "string"},
                },
                "required": ["name", "type", "provider"],
                "additionalProperties": False,
            },
        },
        "projects": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
        "exercises": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
        "quiz": {"type": "array", "minItems": 2, "maxItems": 3, "items": _QUIZ_QUESTION_SCHEMA},
        "estimated_hours": {"type": "integer"},
        "priority": {"type": "string", "enum": ["critical", "high", "medium"]},
    },
    "required": [
        "title", "category", "why_it_matters", "current_gap", "learning_objectives", "milestones", "resources",
        "projects", "exercises", "quiz", "estimated_hours", "priority",
    ],
    "additionalProperties": False,
}

ROADMAP_SCHEMA = {
    "type": "object",
    "properties": {
        "detected_profession": {"type": "string"},
        "detected_industry": {"type": "string"},
        "stages": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string", "enum": STAGE_NAMES},
                    "description": {"type": "string"},
                    "estimated_duration": {"type": "string"},
                    "milestone": {"type": "string"},
                    "topics": {
                        "type": "array",
                        "minItems": TOPICS_PER_STAGE,
                        "maxItems": TOPICS_PER_STAGE,
                        "items": _TOPIC_SCHEMA,
                    },
                },
                "required": ["stage", "description", "estimated_duration", "milestone", "topics"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["detected_profession", "detected_industry", "stages"],
    "additionalProperties": False,
}


def _build_prompt(
    target_role: str,
    industry: str,
    experience_level: str,
    resume_text: str,
    resume_skills: list[str],
    missing_skills: list[str],
    jd_content: str,
    skill_assessment_summary: str | None,
    interview_summary: str | None,
) -> str:
    role_label = target_role or "the candidate's target role"
    industry_label = f" in the {industry} industry" if industry else ""
    level_label = f" ({experience_level} level)" if experience_level else ""

    context_blocks = [
        f"TARGET ROLE (highest priority — the roadmap must cover everything expected of this role, "
        f"even skills not present anywhere else in this context): {role_label}{industry_label}{level_label}",
    ]
    if jd_content:
        context_blocks.append(f"Target job description:\n{jd_content[:2000]}")
    if resume_skills:
        context_blocks.append(f"Skills already on the candidate's resume (do not re-teach these from scratch): {', '.join(resume_skills)}")
    if resume_text:
        context_blocks.append(f"Resume (for background/experience level context only, not the primary source of truth):\n{resume_text[:2500]}")
    if missing_skills:
        context_blocks.append(f"Skill gaps identified against the target job (prioritize these): {', '.join(missing_skills)}")
    if skill_assessment_summary:
        context_blocks.append(f"Latest skill assessment results (weak areas to reinforce):\n{skill_assessment_summary}")
    if interview_summary:
        context_blocks.append(f"Latest mock interview feedback (areas that need work):\n{interview_summary}")

    context = "\n\n".join(context_blocks)

    return f"""STEP 1 — Before writing anything else, determine this candidate's actual profession, industry, and
career field. Use the TARGET ROLE if one is given; otherwise infer it from the resume's job titles, listed skills,
and experience descriptions. Do NOT default to software engineering — that is only correct if the evidence actually
points there. A Business Administration graduate needs a roadmap about business analytics, strategic planning, and
financial management; a marketer needs SEO, campaigns, and analytics; an accountant needs financial reporting,
taxation, and auditing — none of those should ever come back as a programming/web-development roadmap. Record your
conclusion in the "detected_profession" (a specific role/title, e.g. "Business Analyst", "Marketing Coordinator",
"Staff Accountant", "Backend Engineer" — never something vague like "Professional") and "detected_industry" fields.

STEP 2 — Design a complete, realistic learning roadmap to take this candidate from their current level to fully
job-ready for the profession you just detected. Build the roadmap around what a working professional in THAT
profession is actually expected to know, not just what's already on the resume — if the profession requires
something the resume doesn't mention, include it anyway. Every stage and topic must be grounded in the DETECTED
profession, never generic tech content unless the detected profession genuinely is a technical/engineering one.

{context}

Structure the roadmap into exactly 4 stages, in this exact order: Foundation, Intermediate, Advanced, Job Ready.
- Foundation: core fundamentals and prerequisites for the detected profession — what someone needs before anything
  else, expressed in that profession's own terms (e.g. financial literacy and business communication for a business
  role, not version control or data structures unless the profession is genuinely technical).
- Intermediate: the core, everyday skills of the role.
- Advanced: specialized, differentiating skills — including the identified skill gaps and anything that separates
  a strong candidate from an average one for this specific profession.
- Job Ready: interview readiness, portfolio/case-study building, a capstone project or case study appropriate to
  the detected profession (a business case study for a business role, a campaign case study for marketing, a
  system-design exercise only for an engineering role, etc.), and polish — the final stretch before applying.

For each stage, write a short description, a realistic estimated_duration (e.g. "2-3 weeks"), and a milestone: a
concrete, checkable capability statement specific to the detected profession (e.g. "You can now build and deploy a
full REST API with authentication" for an engineering role, or "You can build a full financial model and defend its
assumptions" for a finance role — never a generic statement, and never a technical one unless the profession is
technical).

For each stage, generate exactly {TOPICS_PER_STAGE} topics. Each topic needs:
- title: a specific topic, not a vague category (e.g. "REST API design and versioning" or "Financial statement
  analysis", not "Backend basics" or "Finance stuff").
- category: a short label grouping this topic for the UI (e.g. "Financial Literacy", "Analytics", "Communication",
  "Tools & Software", "Technical Depth" — pick whatever labels genuinely fit the detected profession, don't force
  software-engineering-flavored categories onto a non-technical roadmap).
- why_it_matters: 1-2 sentences on why this specific topic matters for THIS role, grounded in real industry practice.
- current_gap: 1-2 sentences naming the candidate's SPECIFIC current gap for this exact topic — grounded in what
  their resume, skill assessment, or interview feedback actually shows (or doesn't show), not a generic "you don't
  know this yet." If they have partial/adjacent experience, say so specifically instead of treating them as a
  total beginner.
- learning_objectives: 2-4 concrete, measurable things the candidate will be able to do after this topic.
- milestones: three short, concrete, checkable capability statements for THIS topic specifically — "beginner"
  (can follow guided material without getting stuck), "intermediate" (can build something real with it mostly
  unassisted), "advanced" (can debug non-trivial issues and explain real trade-offs) — each one specific to this
  topic, not generic.
- resources: 2-3 realistic, named learning resources (real course names, official docs, well-known books, YouTube
  channels/series, or specific articles) — mix free and paid, and vary resource type (Course/Free/Book/Docs/Cert/
  Video/Article/Tutorial) rather than always picking the same type. Prefer including at least one video/tutorial
  and one documentation/article source when realistic for the topic, alongside a deeper course/book option.
- projects: 1-2 concrete project ideas that apply this topic in a portfolio-worthy way.
- exercises: 1-2 smaller practical exercises to build the skill incrementally before the project.
- quiz: 2-3 multiple-choice self-check questions that test real understanding of this specific topic (not trivia
  or the topic's name) — each with exactly 4 plausible options, a 0-indexed correct_index, and a short explanation
  of why that answer is correct. These let the candidate self-assess before moving on.
- estimated_hours: a realistic integer number of hours to reach working competence.
- priority: "critical" if this closes an identified skill gap or is core to the role, "high" if it's important but
  not urgent, "medium" if it rounds out the profile.

Ground everything in what real companies actually expect for the DETECTED profession — this should read like a
roadmap a senior practitioner or hiring manager in that specific field would actually endorse, not generic advice
and not a software engineering roadmap wearing a different job title.
"""


_TOPIC_REQUIRED_KEYS = (
    "title", "category", "why_it_matters", "current_gap", "learning_objectives", "milestones",
    "resources", "projects", "exercises", "quiz", "estimated_hours", "priority",
)


def _validate_roadmap(result: dict) -> bool:
    if not result.get("detected_profession") or not isinstance(result.get("detected_industry"), str):
        return False
    stages = result.get("stages", [])
    if len(stages) != 4:
        return False
    if [s.get("stage") for s in stages] != STAGE_NAMES:
        return False
    for stage in stages:
        topics = stage.get("topics", [])
        if len(topics) != TOPICS_PER_STAGE:
            return False
        for topic in topics:
            if not all(key in topic for key in _TOPIC_REQUIRED_KEYS):
                return False
            if not all(level in topic["milestones"] for level in ("beginner", "intermediate", "advanced")):
                return False
    return True


def _roadmap_via_groq(
    target_role: str,
    industry: str,
    experience_level: str,
    resume_text: str,
    resume_skills: list[str],
    missing_skills: list[str],
    jd_content: str,
    skill_assessment_summary: str | None,
    interview_summary: str | None,
) -> dict:
    """Groq equivalent of the Gemini call in generate_learning_roadmap — same
    prompt (reuses _build_prompt exactly), adapted only in how the JSON shape
    is requested/parsed, since Groq's OpenAI-compatible API has JSON *mode*
    but not Gemini's strict response_json_schema enforcement."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_prompt(
        target_role, industry, experience_level, resume_text, resume_skills,
        missing_skills, jd_content, skill_assessment_summary, interview_summary,
    ) + groq_json_instructions(
        '"detected_profession" (string, a specific role/title — never software engineering unless the evidence '
        'actually points there), "detected_industry" (string), and "stages" — an array of exactly 4 objects, in '
        'this exact order and with these exact "stage" values: "Foundation", "Intermediate", "Advanced", '
        '"Job Ready". Each stage object needs "stage" (string), "description" (string), "estimated_duration" '
        '(string), "milestone" (string), and "topics" (an array of '
        f'exactly {TOPICS_PER_STAGE} objects, each with "title" (string), "category" (string), "why_it_matters" '
        '(string), "current_gap" (string), "learning_objectives" (array of strings), "milestones" (object with '
        '"beginner", "intermediate", "advanced" string fields), "resources" (array of objects with "name", "type" '
        '— one of Course/Free/Book/Docs/Cert/Video/Article/Tutorial — and "provider" strings), "projects" (array '
        'of strings), "exercises" (array of strings), "quiz" (array of 2-3 objects, each with "question" (string), '
        '"options" (array of exactly 4 strings), "correct_index" (0-indexed integer), and "explanation" (string)), '
        '"estimated_hours" (integer), and "priority" ("critical", "high", or "medium"))'
    )

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        # Groq's free tier caps at 12000 tokens/minute for prompt + max_tokens COMBINED (not
        # just completion) — 12000 here left no headroom for the prompt itself and got rejected
        # outright with a 413. 8000 leaves comfortable room for the (often 1000-2000 token)
        # prompt while still fitting the larger per-topic content (current_gap/milestones/quiz).
        max_tokens=8000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    if not _validate_roadmap(result):
        raise ValueError("Groq response did not match the required roadmap shape")
    return result


def _try_groq_roadmap(
    target_role: str,
    industry: str,
    experience_level: str,
    resume_text: str,
    resume_skills: list[str],
    missing_skills: list[str],
    jd_content: str,
    skill_assessment_summary: str | None,
    interview_summary: str | None,
) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing rule-based roadmap builder instead of surfacing an error."""
    try:
        result = _roadmap_via_groq(
            target_role, industry, experience_level, resume_text, resume_skills,
            missing_skills, jd_content, skill_assessment_summary, interview_summary,
        )
        logger.info("learning_roadmap_ai.generate_learning_roadmap served by groq (gemini quota/rate-limit hit)")
        return result
    except Exception:
        logger.warning("learning_roadmap_ai.generate_learning_roadmap: groq fallback also failed", exc_info=True)
        return None


def generate_learning_roadmap(
    target_role: str,
    industry: str,
    experience_level: str,
    resume_text: str,
    resume_skills: list[str],
    missing_skills: list[str],
    jd_content: str,
    skill_assessment_summary: str | None = None,
    interview_summary: str | None = None,
    ai_enabled: bool = True,
) -> dict | None:
    """Returns {"stages": [...]} or None if AI is unavailable/disabled/fails —
    callers should fall back to app/services/learning_roadmap.py's rule-based
    builder in that case."""
    if not ai_enabled:
        return None

    gemini_keys = _gemini_api_keys()
    if not gemini_keys:
        return None

    for api_key in gemini_keys:
        try:
            client = _client(api_key)
            response = client.models.generate_content(
                model=MODEL,
                contents=_build_prompt(
                    target_role, industry, experience_level, resume_text, resume_skills,
                    missing_skills, jd_content, skill_assessment_summary, interview_summary,
                ),
                config=genai_types.GenerateContentConfig(
                    # Raised from 8000 — current_gap/milestones/quiz roughly doubled the
                    # per-topic output size across all 16 topics in a roadmap.
                    max_output_tokens=12000,
                    response_mime_type="application/json",
                    response_json_schema=ROADMAP_SCHEMA,
                    thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                ),
            )
            result = json.loads(response.text)
            if not _validate_roadmap(result):
                return None
            logger.info("learning_roadmap_ai.generate_learning_roadmap served by gemini")
            return result
        except genai_errors.ClientError as e:
            if e.code == 429:
                continue  # try the next configured Gemini key, if any
            logger.info("learning_roadmap_ai.generate_learning_roadmap served by fallback (gemini ClientError, code=%s)", e.code)
            return None
        except Exception:
            logger.info("learning_roadmap_ai.generate_learning_roadmap served by fallback (unexpected gemini error)")
            return None

    # Every configured Gemini key hit a 429 — try Groq before giving up.
    return _try_groq_roadmap(
        target_role, industry, experience_level, resume_text, resume_skills,
        missing_skills, jd_content, skill_assessment_summary, interview_summary,
    )
