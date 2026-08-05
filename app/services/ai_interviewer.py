"""
Conversational mock-interview service. Follows the same shape as
ai_suggestions.py / resume_builder.py: Gemini SDK, module-level MODEL
constant, a GEMINI_API_KEY gate, and a per-exception-type fallback — except
here the fallback is an interactive experience too (it walks the existing
rule-based question bank one question at a time) rather than a one-shot
response, so the practice session still feels live even without an API key
configured.

Each turn returns structured {feedback, question} rather than one blended
message: `feedback` critiques the candidate's previous answer (empty on the
very first turn, since there's nothing to critique yet), `question` is the
next question to ask (or the closing remarks once the session is done). The
frontend shows these as two distinct pieces rather than a growing chat log.
"""
import os
import json
import logging
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from app.services.interview_questions import build_interview_questions
from app.services.groq_client import GROQ_MODEL, groq_client, groq_json_instructions

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-latest"
MAX_QUESTIONS = 7

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


TURN_SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {"type": "string"},
        "question": {"type": "string"},
    },
    "required": ["feedback", "question"],
    "additionalProperties": False,
}


def _build_system_prompt(resume_text: str, jd_content: str, jd_title: str, missing_skills: list, preferred_language: str | None) -> str:
    gaps = ", ".join(missing_skills[:10]) if missing_skills else "none noted"
    if preferred_language:
        language_rule = (
            f"- The candidate's browser/UI language is '{preferred_language}'. Ask your first "
            "question in that language. From then on, always match whichever language the candidate actually "
            "speaks their answers in, even if they switch mid-conversation — language is not fixed for the "
            "whole session."
        )
    else:
        language_rule = (
            "- Default to English for your first message. From then on, always match whichever language the "
            "candidate actually speaks their answers in, even if they switch mid-conversation."
        )
    return f"""You are an experienced, rigorous interviewer conducting a realistic, appropriately difficult mock interview for a {jd_title or "the candidate's target"} position.

Candidate's resume:
{resume_text[:4000] if resume_text else "(not provided)"}

Job description:
{jd_content[:2500] if jd_content else "(not provided)"}

Skills the job wants that aren't clearly on the resume: {gaps}

You must respond with two fields every turn: "feedback" and "question".

feedback:
- On the very first turn (the candidate hasn't answered anything yet), set feedback to an empty string.
- On every later turn, critique the candidate's PREVIOUS answer specifically: 2-4 sentences covering (a) what
  was genuinely strong about it, if anything, (b) what a strong answer to that question would have included
  that theirs didn't (specifics, metrics, structure, depth), and (c) one concrete, actionable suggestion for
  improving that kind of answer. Be honest and specific — reference what they actually said, never generic
  platitudes like "good job" or "keep practicing."
- If the question had a factually correct or technically right answer, open by plainly stating whether the
  candidate's answer was correct, partially correct, or wrong — don't bury this in vague language or let a
  wrong answer sound like a pass. If they got it wrong, say so directly and then state what the correct
  answer actually is before moving on to the rest of the critique.

question:
- Exactly ONE question, specific and appropriately challenging for the seniority level implied by the resume
  and job description — not a generic templated question. Ground it in specifics: their actual resume history,
  technical depth on skills they listed, system-design/architecture thinking, or the gap skills above.
- Vary question type and difficulty across the session — don't ask two similarly-shaped questions in a row,
  and escalate difficulty as the interview progresses rather than staying at the same level throughout.
- Once roughly {MAX_QUESTIONS} exchanges have happened, instead of a new question, put a short, honest
  closing assessment here (building on your last feedback) and thank them — no question in that case.
{language_rule}
"""


def _fallback_questions(missing_skills: list, resume_skills: list, jd_title: str) -> list:
    return build_interview_questions(missing_skills or [], resume_skills or [], jd_title or "")[:MAX_QUESTIONS]


def _fallback_reply(conversation: list, missing_skills: list, resume_skills: list, jd_title: str) -> dict:
    questions = _fallback_questions(missing_skills, resume_skills, jd_title)
    answered_count = len([m for m in conversation if m.get("role") == "candidate"])

    if not questions:
        return {
            "feedback": "",
            "question": "I don't have enough detail from your resume or the job description to build questions yet — save an analysis from your dashboard first.",
            "source": "fallback",
            "done": True,
        }

    if answered_count >= len(questions):
        return {
            "feedback": "",
            "question": "That's the end of this practice session — nice work getting through all the questions. Review the feedback you got along the way, or start a new session for a fresh set.",
            "source": "fallback",
            "done": True,
        }

    q = questions[answered_count]
    feedback = "" if answered_count == 0 else "Thanks for sharing that — without AI feedback configured, I can't critique your specific answer, but here's the next question."
    return {"feedback": feedback, "question": q["question"], "source": "fallback", "done": False}


def _interviewer_reply_via_groq(
    resume_text: str,
    jd_content: str,
    jd_title: str,
    missing_skills: list,
    conversation: list,
    preferred_language: str | None,
) -> dict:
    """Groq equivalent of the Gemini call in get_interviewer_reply — same system
    prompt (reuses _build_system_prompt exactly) and conversation history,
    adapted only in transport (Gemini's role/parts format vs. OpenAI-style
    messages) and how the JSON shape is requested/parsed."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    system_prompt = _build_system_prompt(
        resume_text, jd_content, jd_title, missing_skills, preferred_language
    ) + groq_json_instructions('"feedback" (string), "question" (string)')

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": "assistant" if m["role"] == "interviewer" else "user", "content": m["content"]} for m in conversation
    )
    if not conversation:
        messages.append({"role": "user", "content": "Please begin the interview."})

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(response.choices[0].message.content)
    if "feedback" not in parsed or "question" not in parsed:
        raise ValueError("Groq response missing required keys")
    return parsed


def _try_groq_interviewer_reply(
    resume_text: str,
    jd_content: str,
    jd_title: str,
    missing_skills: list,
    conversation: list,
    preferred_language: str | None,
) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the rule-based question bank instead of surfacing an error."""
    try:
        parsed = _interviewer_reply_via_groq(resume_text, jd_content, jd_title, missing_skills, conversation, preferred_language)
        answered_count = len([m for m in conversation if m.get("role") == "candidate"])
        done = answered_count >= MAX_QUESTIONS
        logger.info("ai_interviewer.get_interviewer_reply served by groq (gemini quota/rate-limit hit)")
        return {"feedback": parsed["feedback"], "question": parsed["question"], "source": "ai", "done": done}
    except Exception:
        logger.warning("ai_interviewer.get_interviewer_reply: groq fallback also failed", exc_info=True)
        return None


def get_interviewer_reply(
    resume_text: str,
    jd_content: str,
    jd_title: str,
    missing_skills: list,
    resume_skills: list,
    conversation: list,
    ai_enabled: bool = True,
    preferred_language: str | None = None,
) -> dict:
    """conversation is a list of {"role": "interviewer"|"candidate", "content": str},
    in chronological order, not including the reply being generated now. Falls back to the
    rule-based question bank if AI features have been disabled platform-wide (ai_enabled=False,
    set via Admin Settings) or no server-wide GEMINI_API_KEY is configured. preferred_language
    (e.g. a browser locale like "tr-TR") seeds the language of the opening message; the AI matches
    whatever language the candidate actually speaks in from then on. The rule-based fallback
    has no translations and always runs in English regardless of this setting, and can't
    critique specific answers (no AI available), only announce it can't."""
    if not ai_enabled:
        return _fallback_reply(conversation, missing_skills, resume_skills, jd_title)

    gemini_keys = _gemini_api_keys()
    if not gemini_keys:
        return _fallback_reply(conversation, missing_skills, resume_skills, jd_title)

    for api_key in gemini_keys:
        try:
            client = _client(api_key)

            contents = [
                {"role": "model" if m["role"] == "interviewer" else "user", "parts": [{"text": m["content"]}]}
                for m in conversation
            ]
            if not contents:
                contents = [{"role": "user", "parts": [{"text": "Please begin the interview."}]}]

            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=4000,
                    system_instruction=_build_system_prompt(resume_text, jd_content, jd_title, missing_skills, preferred_language),
                    response_mime_type="application/json",
                    response_json_schema=TURN_SCHEMA,
                ),
            )
            parsed = json.loads(response.text)

            answered_count = len([m for m in conversation if m.get("role") == "candidate"])
            done = answered_count >= MAX_QUESTIONS

            logger.info("ai_interviewer.get_interviewer_reply served by gemini")
            return {"feedback": parsed["feedback"], "question": parsed["question"], "source": "ai", "done": done}
        except genai_errors.ClientError as e:
            if e.code == 429:
                continue  # try the next configured Gemini key, if any
            logger.info("ai_interviewer.get_interviewer_reply served by fallback (gemini ClientError, code=%s)", e.code)
            return _fallback_reply(conversation, missing_skills, resume_skills, jd_title)
        except genai_errors.ServerError:
            logger.info("ai_interviewer.get_interviewer_reply served by fallback (gemini ServerError)")
            return _fallback_reply(conversation, missing_skills, resume_skills, jd_title)
        except Exception:
            logger.info("ai_interviewer.get_interviewer_reply served by fallback (unexpected gemini error)")
            return _fallback_reply(conversation, missing_skills, resume_skills, jd_title)

    # Every configured Gemini key hit a 429 — try Groq before giving up.
    groq_result = _try_groq_interviewer_reply(resume_text, jd_content, jd_title, missing_skills, conversation, preferred_language)
    if groq_result is not None:
        return groq_result
    logger.info("ai_interviewer.get_interviewer_reply served by fallback (all gemini keys quota/rate-limited)")
    return _fallback_reply(conversation, missing_skills, resume_skills, jd_title)
