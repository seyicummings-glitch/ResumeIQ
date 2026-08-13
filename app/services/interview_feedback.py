"""
Post-interview feedback report. Runs once, after a voice mock-interview
session ends, over the full transcript — separate from ai_interviewer.py's
turn-by-turn chat replies. Follows the same shape as the rest of this app's
AI services: Gemini SDK, a GEMINI_API_KEY gate, structured JSON output via a
schema, and a rule-based fallback so the feature still returns something
useful without an API key configured.
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


FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_assessment": {"type": "string"},
        "overall_score": {"type": "integer"},
        "technical_performance": {"type": "string"},
        "communication_assessment": {"type": "string"},
        "confidence_assessment": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "areas_to_improve": {"type": "array", "items": {"type": "string"}},
        "recommended_improvements": {"type": "array", "items": {"type": "string"}},
        "study_topics": {"type": "array", "items": {"type": "string"}},
        "role_knowledge_tips": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overall_assessment", "overall_score", "technical_performance", "communication_assessment",
        "confidence_assessment", "strengths", "areas_to_improve", "recommended_improvements",
        "study_topics", "role_knowledge_tips",
    ],
    "additionalProperties": False,
}


def _build_prompt(transcript: list, resume_text: str, jd_title: str, jd_content: str, missing_skills: list) -> str:
    transcript_text = "\n".join(
        f"{'Interviewer' if m.get('role') == 'interviewer' else 'Candidate'}: {m.get('content', '')}"
        for m in transcript
    ) or "(no exchanges recorded)"
    gaps = ", ".join(missing_skills[:10]) if missing_skills else "none noted"

    role_label = jd_title or "the candidate's target"
    return (
        "You just finished conducting a mock interview for a "
        f"{role_label} position. Review the full transcript below and give the "
        "candidate honest, constructive, specific post-interview feedback — like a hiring manager debrief, "
        "not generic encouragement.\n\n"
        f"Candidate's resume:\n{resume_text[:3000] if resume_text else '(not provided)'}\n\n"
        f"Job description:\n{jd_content[:2000] if jd_content else '(not provided)'}\n\n"
        f"Skills the job wants that weren't clearly on the resume: {gaps}\n\n"
        f"Full interview transcript:\n{transcript_text[:6000]}\n\n"
        "Produce:\n"
        "- overall_assessment: 2-4 sentences, honest and specific to what they actually said.\n"
        "- overall_score: an integer 0-100 reflecting overall interview performance across the whole session — "
        "be a realistic, discriminating grader (a candidate who gave thin, unstructured answers throughout "
        "should not score above ~50; a candidate who was consistently sharp, specific, and well-structured can "
        "score 85+). Base it on the actual transcript, not on effort or participation alone.\n"
        "- technical_performance: 1-3 sentences assessing technical knowledge and problem-solving ability shown "
        "in the answers — depth, accuracy, and how they reasoned through technical questions. If the session had "
        "no technical questions, say so briefly instead of inventing an assessment.\n"
        "- communication_assessment: 1-3 sentences on clarity, structure, and how well they explained themselves "
        "— e.g. whether answers were organized (STAR-style for behavioral ones), concise vs. rambling, and easy "
        "to follow.\n"
        "- confidence_assessment: 1-3 sentences on how confident, direct, and decisive their answers came "
        "across — hedging and vagueness read as low confidence; specific, owned claims read as high confidence.\n"
        "- strengths: 2-4 concrete things they did well in their answers (reference specifics, not platitudes).\n"
        "- areas_to_improve: 2-4 specific weaknesses based on how they actually answered (e.g. vague answers, "
        "missing structure, weak examples, factual errors) — not generic interview advice.\n"
        "- recommended_improvements: 2-4 concrete, actionable next steps the candidate should do before their "
        "real interview to fix the weaknesses above (e.g. practice a specific type of question, learn a "
        "specific concept, tighten a specific habit) — actions, not restated criticism.\n"
        "- study_topics: 2-5 specific skills, tools, or concepts worth studying before the real interview, "
        "prioritizing the job's gap skills and anything they stumbled on.\n"
        "- role_knowledge_tips: 2-4 pieces of extra knowledge about this type of role or domain that would "
        "help them sound more credible — real, specific insight, not filler."
    )


def _fallback_feedback(transcript: list, missing_skills: list, message: str) -> dict:
    answered_count = len([m for m in transcript if m.get("role") == "candidate"])
    return {
        "overall_assessment": (
            f"{message} You answered {answered_count} question{'s' if answered_count != 1 else ''} in this "
            "session — review your answers above and compare them against the job description."
        ),
        # No AI available to actually grade the transcript — None (not a guessed number) so the
        # frontend can show "Not scored" instead of a fabricated score.
        "overall_score": None,
        "technical_performance": "Not available without AI feedback — review your technical answers yourself against the job description.",
        "communication_assessment": "Not available without AI feedback — review your answers for clarity and structure yourself.",
        "confidence_assessment": "Not available without AI feedback.",
        "strengths": ["You completed a full mock interview session, which is real practice on its own."],
        "areas_to_improve": [
            "Without AI feedback available, review your own answers for clarity, structure, and specific examples."
        ],
        "recommended_improvements": [
            "Re-run this session once AI feedback is available for a real critique of your answers."
        ],
        "study_topics": missing_skills[:5] if missing_skills else ["Re-read the job description and note any unfamiliar requirements."],
        "role_knowledge_tips": [],
        "source": "fallback",
    }


def _feedback_via_groq(transcript: list, resume_text: str, jd_title: str, jd_content: str, missing_skills: list) -> dict:
    """Groq equivalent of the Gemini call in generate_interview_feedback — same
    prompt (reuses _build_prompt exactly), adapted only in how the JSON shape
    is requested/parsed."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_prompt(transcript, resume_text, jd_title, jd_content, missing_skills) + groq_json_instructions(
        '"overall_assessment" (string), "overall_score" (integer 0-100), "technical_performance" (string), '
        '"communication_assessment" (string), "confidence_assessment" (string), "strengths" (array of strings), '
        '"areas_to_improve" (array of strings), "recommended_improvements" (array of strings), '
        '"study_topics" (array of strings), "role_knowledge_tips" (array of strings)'
    )

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    for key in (
        "overall_assessment", "overall_score", "technical_performance", "communication_assessment",
        "confidence_assessment", "strengths", "areas_to_improve", "recommended_improvements",
        "study_topics", "role_knowledge_tips",
    ):
        if key not in result:
            raise ValueError(f"Groq response missing required key: {key}")
    return result


def _try_groq_feedback(transcript: list, resume_text: str, jd_title: str, jd_content: str, missing_skills: list) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the existing rule-based fallback instead of surfacing an error."""
    try:
        result = _feedback_via_groq(transcript, resume_text, jd_title, jd_content, missing_skills)
        result["source"] = "ai"
        logger.info("interview_feedback.generate_interview_feedback served by groq (gemini quota/rate-limit hit)")
        return result
    except Exception:
        logger.warning("interview_feedback.generate_interview_feedback: groq fallback also failed", exc_info=True)
        return None


def generate_interview_feedback(
    transcript: list,
    resume_text: str,
    jd_title: str,
    jd_content: str,
    missing_skills: list,
    ai_enabled: bool = True,
) -> dict:
    """transcript is a list of {"role": "interviewer"|"candidate", "content": str} for the
    whole completed session. Falls back to a lightweight, honest summary (not AI-generated
    insight) if AI features are disabled platform-wide, no server-wide GEMINI_API_KEY is
    configured, or the call fails."""
    if not ai_enabled:
        return _fallback_feedback(transcript, missing_skills, "AI interview feedback has been disabled by the administrator.")

    gemini_keys = _gemini_api_keys()
    if not gemini_keys:
        return _fallback_feedback(transcript, missing_skills, "AI interview feedback is not configured (no API key set).")

    for api_key in gemini_keys:
        try:
            client = _client(api_key)
            response = client.models.generate_content(
                model=MODEL,
                contents=_build_prompt(transcript, resume_text, jd_title, jd_content, missing_skills),
                config=genai_types.GenerateContentConfig(
                    # 1500 wasn't enough headroom once the model's internal "thinking"
                    # tokens are counted against the same budget — raised the same way
                    # the other AI services in this app were fixed.
                    max_output_tokens=4000,
                    response_mime_type="application/json",
                    response_json_schema=FEEDBACK_SCHEMA,
                    thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                ),
            )
            result = json.loads(response.text)
            result["source"] = "ai"
            logger.info("interview_feedback.generate_interview_feedback served by gemini")
            return result
        except genai_errors.ClientError as e:
            if e.code == 429:
                continue  # try the next configured Gemini key, if any
            return _fallback_feedback(transcript, missing_skills, "AI feedback is temporarily rate-limited or returned an error.")
        except genai_errors.ServerError:
            return _fallback_feedback(transcript, missing_skills, "Could not reach the AI service for feedback.")
        except Exception:
            return _fallback_feedback(transcript, missing_skills, "AI interview feedback is temporarily unavailable.")

    # Every configured Gemini key hit a 429 — try Groq before giving up.
    groq_result = _try_groq_feedback(transcript, resume_text, jd_title, jd_content, missing_skills)
    if groq_result is not None:
        return groq_result
    return _fallback_feedback(transcript, missing_skills, "AI feedback is temporarily rate-limited or returned an error.")
