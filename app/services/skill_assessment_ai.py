"""
AI-generated, AI-graded skill assessment. Follows the same shape as the rest
of this app's AI services (ai_interviewer.py, resume_builder.py): Gemini SDK,
a GEMINI_API_KEY gate, structured JSON output, and a rule-based fallback.

Two entry points:
- generate_assessment_questions(...) builds a user-chosen total number of
  questions (default 15, see DEFAULT_TOTAL_COUNT) across four categories
  (Technical, Scenario-Based, Problem-Solving, Behavioral), grounded
  primarily in the candidate's target role/industry — not the resume alone,
  so the assessment covers what the role actually requires even when the CV
  doesn't mention it. Each question carries a hidden grading rubric
  (expected_answer_points) that's never shown to the user —
  app/routes/skill_assessment.py strips it before the question set is
  returned, and grade_assessment_answers reads it back from the
  DB-persisted session rather than trusting anything the client submits.
- grade_assessment_answers(...) scores every answer in one batch call against
  those rubrics: correctness, relevance, completeness, and technical accuracy.
  A blank, off-topic, or nonsensical answer is graded near zero — there's no
  length-based or participation credit anywhere in this path.

Both fall back to app/services/skill_assessment.py's static multiple-choice
bank when AI is disabled/unavailable, where correctness is exact-match (so
"gives a score for a wrong answer" is structurally impossible in fallback
mode too, just with less personalized/harder questions).
"""
import os
import json
import logging
import random
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from app.services.groq_client import GROQ_MODEL, groq_client, groq_json_instructions

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-latest"

# The SDK's default retry policy (5 attempts, exponential backoff up to 60s) is
# meant for transient errors — but a 429 caused by the daily quota being fully
# exhausted will never succeed no matter how many times it's retried within
# that window, so it just adds up to ~60s of dead time before falling back to
# the rule-based question bank. Capping attempts keeps that worst case short.
_RETRY_OPTIONS = genai_types.HttpRetryOptions(attempts=2)


def _client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key, http_options=genai_types.HttpOptions(retry_options=_RETRY_OPTIONS))


DEFAULT_TOTAL_COUNT = 15
MIN_TOTAL_COUNT = 5
MAX_TOTAL_COUNT = 25

_TYPE_RATIOS = {"technical": 0.4, "scenario": 0.2, "problem_solving": 0.2, "behavioral": 0.2}


def distribute_counts(total_count: int) -> dict[str, int]:
    """Splits a user-chosen total into per-category counts using a fixed
    40/20/20/20 (technical/scenario/problem-solving/behavioral) ratio, always
    summing to exactly total_count with at least 1 question per category."""
    total_count = max(MIN_TOTAL_COUNT, min(MAX_TOTAL_COUNT, total_count))
    counts = {key: max(1, round(total_count * ratio)) for key, ratio in _TYPE_RATIOS.items()}
    counts["technical"] += total_count - sum(counts.values())
    return counts


def _question_array_schema(count: int, include_difficulty: bool) -> dict:
    properties = {
        "category": {"type": "string"},
        "question": {"type": "string"},
        "expected_answer_points": {"type": "string"},
    }
    required = ["category", "question", "expected_answer_points"]
    if include_difficulty:
        properties["difficulty"] = {"type": "string", "enum": ["intermediate", "advanced"]}
        required.append("difficulty")

    return {
        "type": "array",
        "minItems": count,
        "maxItems": count,
        "items": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


def _build_generation_schema(counts: dict[str, int]) -> dict:
    return {
        "type": "object",
        "properties": {
            "technical_questions": _question_array_schema(counts["technical"], include_difficulty=True),
            "scenario_questions": _question_array_schema(counts["scenario"], include_difficulty=False),
            "problem_solving_questions": _question_array_schema(counts["problem_solving"], include_difficulty=True),
            "behavioral_questions": _question_array_schema(counts["behavioral"], include_difficulty=False),
        },
        "required": ["technical_questions", "scenario_questions", "problem_solving_questions", "behavioral_questions"],
        "additionalProperties": False,
    }


def _build_generation_prompt(
    target_role: str,
    industry: str,
    experience_level: str,
    resume_text: str,
    resume_skills: list[str],
    missing_skills: list[str],
    jd_content: str,
    recent_questions: list[str],
    counts: dict[str, int],
) -> str:
    role_label = target_role or "the candidate's target role"
    industry_label = f" in {industry}" if industry else ""
    level_label = f", {experience_level} level" if experience_level else ""

    # Shuffling the order (rather than always leading with the same skill)
    # measurably helps push the model toward genuinely different questions on
    # a retake, on top of the explicit avoid-list below.
    shuffled_resume_skills = list(resume_skills)
    random.shuffle(shuffled_resume_skills)
    shuffled_missing_skills = list(missing_skills)
    random.shuffle(shuffled_missing_skills)

    skills_list = ", ".join(shuffled_resume_skills) if shuffled_resume_skills else "(none detected)"
    gaps_list = ", ".join(shuffled_missing_skills) if shuffled_missing_skills else "(none noted)"

    avoid_block = ""
    if recent_questions:
        shuffled_recent = list(recent_questions)
        random.shuffle(shuffled_recent)
        avoid_block = (
            "\n\nThis candidate has taken this assessment before. You MUST generate a genuinely fresh set this "
            "time — do not reuse or lightly reword ANY of the questions below, and do not just swap one gap skill "
            "for another while asking the same underlying question. Change the specific skills tested, the "
            "scenario settings, and the angle of each question. If needed, cover different sub-topics within the "
            "same skill area entirely. Here is what the candidate was already asked — treat all of it as off-limits:\n"
            + "\n".join(f"- {q}" for q in shuffled_recent[:40])
        )

    return f"""Generate a challenging, interview-level skill assessment to evaluate whether this candidate is
qualified for the role of {role_label}{industry_label}{level_label}. This target role is the PRIMARY driver of
every question — cover what a real interviewer would test for this specific role, even for skills the resume
below doesn't mention. The resume is only supporting context, not the source of truth for what to ask.

Candidate's resume (supporting context only):
{resume_text[:4000] if resume_text else "(not provided)"}

Skills detected on the resume: {skills_list}
Skills the target job wants that are missing or unclear on the resume (gaps — prioritize testing these): {gaps_list}

Job description:
{jd_content[:2000] if jd_content else "(not provided)"}

Generate exactly {counts['technical']} Technical questions, {counts['scenario']} Scenario-Based
questions, {counts['problem_solving']} Problem-Solving questions, and {counts['behavioral']} Behavioral
questions ({sum(counts.values())} total).

Technical questions:
- Interview-level difficulty ("intermediate" or "advanced" only — no basic definition trivia). Test applied
  knowledge of the role's core stack: predicting behavior/output, debugging, justifying a design trade-off, or
  explaining the "why" behind a practice — not "what is X".
- Dedicate roughly a third of these to the GAP skills above — test real conceptual understanding even if the
  resume shows no direct experience with them.

Scenario-Based questions:
- Realistic, role-specific situations a professional in this exact role would face on the job (production
  incidents, ambiguous requirements, cross-team friction, technical trade-offs under a deadline). Specific and
  situational, not abstract.

Problem-Solving questions:
- A concrete problem to reason through out loud — an algorithmic/logic challenge, a system/data-flow design
  question, or a "how would you approach X" question appropriate for this role and seniority. Should have real
  depth, not a one-line trivia answer.
- Mark difficulty "intermediate" or "advanced".

Behavioral questions:
- Realistic interview behavioral questions probing ownership, conflict handling, communication, failure/learning,
  or prioritization — specific enough to require a real story, not a generic "tell me about yourself".

For every question, expected_answer_points is 2-4 concise bullet-style points (as one string, separated by "; ")
describing what a strong answer must cover. This is a hidden grading rubric — never phrase it as if the candidate
will see it. For Scenario-Based and Behavioral questions (no single correct answer), describe the qualities a
strong answer would show instead (specific reasoning, ownership, concrete structure).
{avoid_block}
"""


_GENERATION_KEYS = ["technical_questions", "scenario_questions", "problem_solving_questions", "behavioral_questions"]


def _validate_generation_result(result: dict, counts: dict[str, int]) -> bool:
    for key in _GENERATION_KEYS:
        type_key = key.replace("_questions", "")
        if len(result.get(key, [])) != counts[type_key]:
            return False
    return True


def _generate_via_groq(
    target_role: str,
    industry: str,
    experience_level: str,
    resume_text: str,
    resume_skills: list[str],
    missing_skills: list[str],
    jd_content: str,
    recent_questions: list[str],
    counts: dict[str, int],
) -> dict:
    """Groq equivalent of the Gemini call in generate_assessment_questions — same
    prompt (reuses _build_generation_prompt exactly), adapted only in how the
    JSON shape is requested/parsed since Groq's OpenAI-compatible API has JSON
    *mode* but not Gemini's strict response_json_schema enforcement."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_generation_prompt(
        target_role, industry, experience_level, resume_text, resume_skills,
        missing_skills, jd_content, recent_questions, counts,
    ) + groq_json_instructions(
        '"technical_questions", "scenario_questions", "problem_solving_questions", "behavioral_questions" — each '
        'an array of objects with "category" (string), "question" (string), "expected_answer_points" (string), '
        'and (for technical_questions/problem_solving_questions only) "difficulty" ("intermediate" or "advanced")'
    )

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.15,
        max_tokens=4000 + sum(counts.values()) * 250,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    if not _validate_generation_result(result, counts):
        raise ValueError("Groq response did not match the requested question counts")
    return result


def _try_groq_generate(
    target_role: str,
    industry: str,
    experience_level: str,
    resume_text: str,
    resume_skills: list[str],
    missing_skills: list[str],
    jd_content: str,
    recent_questions: list[str],
    counts: dict[str, int],
) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing rule-based question bank instead of surfacing an error."""
    try:
        result = _generate_via_groq(
            target_role, industry, experience_level, resume_text, resume_skills,
            missing_skills, jd_content, recent_questions, counts,
        )
        logger.info("skill_assessment_ai.generate_assessment_questions served by groq (gemini quota/rate-limit hit)")
        return result
    except Exception:
        logger.warning("skill_assessment_ai.generate_assessment_questions: groq fallback also failed", exc_info=True)
        return None


def generate_assessment_questions(
    target_role: str,
    industry: str,
    experience_level: str,
    resume_text: str,
    resume_skills: list[str],
    missing_skills: list[str],
    jd_content: str,
    recent_questions: list[str],
    total_count: int = DEFAULT_TOTAL_COUNT,
    ai_enabled: bool = True,
) -> dict | None:
    """Returns {"technical_questions": [...], "scenario_questions": [...],
    "problem_solving_questions": [...], "behavioral_questions": [...]} with
    hidden expected_answer_points rubrics, or None if AI is unavailable/
    disabled/fails — callers should fall back to the static question bank."""
    if not ai_enabled:
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    counts = distribute_counts(total_count)

    try:
        client = _client(api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=_build_generation_prompt(
                target_role, industry, experience_level, resume_text, resume_skills,
                missing_skills, jd_content, recent_questions, counts,
            ),
            config=genai_types.GenerateContentConfig(
                max_output_tokens=4000 + sum(counts.values()) * 250,
                temperature=1.15,
                response_mime_type="application/json",
                response_json_schema=_build_generation_schema(counts),
                # This structured-JSON generation task doesn't need heavy internal
                # reasoning — "LOW" cut real-world latency roughly in half (measured
                # ~30s -> ~14s for a 15-question request) versus the model's default
                # thinking level, without any loss of output quality/validity.
                thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
            ),
        )
        result = json.loads(response.text)
        if not _validate_generation_result(result, counts):
            return None
        logger.info("skill_assessment_ai.generate_assessment_questions served by gemini")
        return result
    except genai_errors.ClientError as e:
        if e.code == 429:
            groq_result = _try_groq_generate(
                target_role, industry, experience_level, resume_text, resume_skills,
                missing_skills, jd_content, recent_questions, counts,
            )
            if groq_result is not None:
                return groq_result
        logger.info("skill_assessment_ai.generate_assessment_questions served by fallback (gemini ClientError, code=%s)", e.code)
        return None
    except Exception:
        logger.info("skill_assessment_ai.generate_assessment_questions served by fallback (unexpected gemini error)")
        return None


GRADING_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "integer"},
                    "score": {"type": "integer"},
                    "is_correct": {"type": "boolean"},
                    "explanation": {"type": "string"},
                    "correct_answer_or_improvement": {"type": "string"},
                },
                "required": ["question_id", "score", "is_correct", "explanation", "correct_answer_or_improvement"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["results"],
    "additionalProperties": False,
}


def _build_grading_prompt(items: list[dict]) -> str:
    blocks = []
    for item in items:
        blocks.append(
            f"Question ID: {item['id']}\n"
            f"Type: {item['type']}\n"
            f"Question: {item['question']}\n"
            f"What a strong answer must cover (grading rubric — the candidate never saw this): {item['expected_answer_points']}\n"
            f"Candidate's answer: {item['answer'] or '(no answer submitted)'}"
        )
    joined = "\n\n---\n\n".join(blocks)

    return f"""You are a strict, fair technical interviewer grading a candidate's assessment answers. Grade every
question below independently and return a score for each.

STRICT GRADING RULES — apply these exactly, do not be lenient:
- Score reflects correctness, relevance, completeness, technical accuracy, and depth against the rubric —
  nothing else. Length, effort, or confident tone earn NO credit on their own.
- A blank answer, an answer that doesn't address the question, random/gibberish text, or an answer that is
  factually wrong must score 0-10 and is_correct must be false. Do not give partial credit just for attempting.
- A partially correct or incomplete answer (gets the general idea but misses key points from the rubric, or has
  a factual error) scores roughly 30-60.
- A fully correct, complete, accurate, and sufficiently deep answer scores 85-100.
- For scenario-based and behavioral questions (no single correct answer), judge against the rubric's expected
  qualities — a vague, generic, or off-topic response still scores low; a specific, well-reasoned one scores high.

For each question return:
- score: integer 0-100 per the rules above.
- is_correct: true only if score >= 70.
- explanation: 1-3 sentences, specific to what the candidate actually wrote (or didn't write) — never a generic
  platitude.
- correct_answer_or_improvement: for technical/problem-solving questions, state the correct/ideal answer
  concisely. For scenario-based/behavioral questions, give one concrete way the answer could be stronger.

Questions and answers to grade:

{joined}
"""


def _grade_via_groq(items: list[dict]) -> list[dict]:
    """Groq equivalent of the Gemini call in grade_assessment_answers — same
    prompt (reuses _build_grading_prompt exactly), adapted only in how the
    JSON shape is requested/parsed."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_grading_prompt(items) + groq_json_instructions(
        '"results" — an array of objects, one per question, each with "question_id" (integer), "score" '
        '(integer 0-100), "is_correct" (boolean), "explanation" (string), "correct_answer_or_improvement" (string)'
    )

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000 + len(items) * 300,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(response.choices[0].message.content)
    results = parsed.get("results", [])
    if len(results) != len(items):
        raise ValueError("Groq response did not return a result for every item")
    return results


def _try_groq_grade(items: list[dict]) -> list[dict] | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing heuristic grading instead of surfacing an error."""
    try:
        results = _grade_via_groq(items)
        logger.info("skill_assessment_ai.grade_assessment_answers served by groq (gemini quota/rate-limit hit)")
        return results
    except Exception:
        logger.warning("skill_assessment_ai.grade_assessment_answers: groq fallback also failed", exc_info=True)
        return None


def grade_assessment_answers(items: list[dict], ai_enabled: bool = True) -> list[dict] | None:
    """items: [{id, type, question, expected_answer_points, answer}, ...]. Returns
    a list of {question_id, score, is_correct, explanation, correct_answer_or_improvement}
    covering every item, or None if AI is unavailable/disabled/fails."""
    if not ai_enabled or not items:
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        client = _client(api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=_build_grading_prompt(items),
            config=genai_types.GenerateContentConfig(
                max_output_tokens=4000 + len(items) * 300,
                response_mime_type="application/json",
                response_json_schema=GRADING_SCHEMA,
                thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
            ),
        )
        parsed = json.loads(response.text)
        results = parsed.get("results", [])
        if len(results) != len(items):
            return None
        logger.info("skill_assessment_ai.grade_assessment_answers served by gemini")
        return results
    except genai_errors.ClientError as e:
        if e.code == 429:
            groq_result = _try_groq_grade(items)
            if groq_result is not None:
                return groq_result
        logger.info("skill_assessment_ai.grade_assessment_answers served by fallback (gemini ClientError, code=%s)", e.code)
        return None
    except Exception:
        logger.info("skill_assessment_ai.grade_assessment_answers served by fallback (unexpected gemini error)")
        return None
