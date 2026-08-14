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
import re
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
        "is_clarification_request": {"type": "boolean"},
        "feedback": {"type": "string"},
        "question": {"type": "string"},
        "questions_answered": {"type": "integer"},
    },
    "required": ["is_clarification_request", "feedback", "question", "questions_answered"],
    "additionalProperties": False,
}

# Lightweight, keyword-based detector used only by the rule-based fallback (no AI available to
# actually understand intent). The AI path does this classification itself, contextually, via
# the "is_clarification_request" field in TURN_SCHEMA — this regex exists purely so the
# fallback doesn't fall into the same bug (treating "can you explain that?" as a weak answer).
_CLARIFICATION_PATTERN = re.compile(
    r"\b("
    r"explain|"
    r"don'?t understand|do not understand|"
    r"simplify|"
    r"re-?phrase|"
    r"ask (it |that )?(another|different) way|"
    r"say (it|that) (again|differently)|"
    r"what do you mean|"
    r"can you clarify|clarify (that|this|it)|"
    r"give (me |us )?an example|"
    r"not sure (what|i understand)|"
    r"could you repeat|can you repeat|"
    r"come again"
    r")\b",
    re.IGNORECASE,
)


def _is_clarification_request(text: str) -> bool:
    return bool(text) and bool(_CLARIFICATION_PATTERN.search(text))


def _count_real_answers(conversation: list) -> int:
    """How many questions the candidate has actually attempted to answer — clarification
    requests ("can you explain that?", "give me an example") don't count, so a candidate
    who's just asking for help isn't silently marked as having answered and skipped ahead."""
    return len([
        m for m in conversation
        if m.get("role") == "candidate" and not _is_clarification_request(m.get("content", ""))
    ])


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
    return f"""You are an experienced, rigorous interviewer — the kind a real company would actually send: a mix of
recruiter, hiring manager, and technical interviewer — conducting a realistic, appropriately challenging mock
interview for a {jd_title or "the candidate's target"} position. This is a real conversation, not a static quiz:
listen to what the candidate actually says, remember it, and let it shape what you ask and say next.

Candidate's resume:
{resume_text[:4000] if resume_text else "(not provided)"}

Job description:
{jd_content[:2500] if jd_content else "(not provided)"}

Skills the job wants that aren't clearly on the resume: {gaps}

Before asking anything, determine this candidate's actual profession and field from the job title, job
description, and resume above. Do NOT default to software engineering — that is only correct if the evidence
actually points there. A chef gets asked about kitchen operations and food safety, not APIs; an accountant gets
asked about reconciliation and reporting, not databases; a nurse gets asked about patient care and clinical
protocol, not code. Every question you ask must be grounded in that actual profession.

You must respond with four fields every turn: "is_clarification_request", "feedback", "question", and
"questions_answered".

STEP 1 — before anything else, classify the candidate's most recent message (skip this on the very first turn,
before they've said anything at all):
- Is it a genuine attempt to answer the question you just asked — even a short, weak, vague, or wrong one?
  That still counts as an attempt.
- OR is it instead asking YOU for help before attempting one — e.g. "can you explain that?", "I don't
  understand", "can you rephrase it?", "simplify it", "ask it another way", "what do you mean by X?", "give me
  an example", "can you repeat that?" — with no real attempt at an answer alongside it?
A message that both asks for help AND makes a real attempt (e.g. "I think it's about caching, but can you
clarify what you mean by 'distributed'?") is an answer attempt, not a clarification request — address their
question as part of your feedback/next question, but still evaluate what they attempted.

A real senior interviewer never penalizes a candidate for asking a clarifying question — that's normal,
professional behavior, not evasion. Getting this classification right matters: misreading a clarification
request as a weak answer and evaluating it anyway is exactly the mistake to avoid.

is_clarification_request:
- true or false, per the classification in STEP 1. On the very first turn, set this to false.

feedback:
- If is_clarification_request is true: set feedback to an empty string. There is nothing to evaluate yet —
  they haven't answered.
- On the very first turn: empty string.
- Otherwise (a genuine answer attempt was just given): critique it specifically — 2-4 sentences covering (a)
  what was genuinely strong about it, if anything, (b) what a strong answer to that question would have
  included that theirs didn't (specifics, metrics, structure, depth), and (c) one concrete, actionable
  suggestion for improving that kind of answer. Be honest and specific — reference what they actually said,
  never generic platitudes like "good job" or "keep practicing."
  - Where relevant to the question, let your critique reflect the dimension(s) it actually tested — technical
    accuracy/depth, problem-solving approach, clarity and structure of communication, or confidence — without
    turning it into a rigid checklist every time; touch on whichever of these genuinely apply.
  - If the question had a factually correct or technically right answer, open by plainly stating whether the
    candidate's answer was correct, partially correct, or wrong — don't bury this in vague language or let a
    wrong answer sound like a pass. If they got it wrong, say so directly and then state what the correct
    answer actually is before moving on to the rest of the critique.
  - If the answer was short, vague, or thin (but still a real attempt, not a clarification request), do NOT
    claim you "didn't get an answer" or that nothing was said — engage with what they DID say and be explicit
    that it needs more depth, rather than treating it as if it didn't happen.

question:
- If is_clarification_request is true: do NOT ask a new question and do NOT move on. Instead, help them
  understand the SAME question you just asked, like a patient real interviewer would — rephrase it in
  simpler, more concrete language, add brief context on why it's being asked, and/or give a short concrete
  example if that would help, then ask the same underlying question again in this clearer form. Respond
  warmly ("Sure, let me put that another way...", "No problem — for example..."), never as if this were a
  failure on their part. If they've already asked for clarification on this SAME question before (check the
  conversation history), go even simpler and more concrete this time — break it into a smaller, more specific
  sub-question — rather than repeating the same rephrasing again.
- Otherwise, exactly ONE question. Two kinds are valid, and you should choose based on the candidate's last
  answer:
  (1) A direct follow-up that digs into what they just said — when their answer was vague, thin, name-dropped
  a project/technology without detail, or (for a behavioral question) lacked a clear situation/task/action/
  result. Ask for the specific missing piece (e.g. "What was the measurable result?" or "Walk me through the
  actual steps you took") rather than the STAR acronym itself — most candidates respond better to a concrete
  prompt than to jargon.
  (2) A fresh question once you've gotten sufficient depth on the current topic — specific and appropriately
  challenging for the seniority level implied by the resume and job description, never generic or templated.
  Ground it in specifics: their actual resume history, depth on skills/tools/methods they listed relevant to
  their actual profession, scenario or judgment-call questions realistic for that profession (system-design/
  architecture thinking only if the profession is genuinely technical/engineering), behavioral/soft-skill
  scenarios, or the gap skills above.
  - Cover a realistic mix across the session — technical/hard-skill questions, behavioral questions about past
    experience, and role- or domain-specific questions grounded in the job description — the way a real
    interview loop would, not one category repeated the whole time.
  - Never repeat a question, or a near-duplicate of one, you already asked earlier in this conversation — check
    the conversation history above before choosing.
  - Adapt difficulty to how the candidate is actually doing, not just a fixed escalation: if their recent
    answers have been strong, specific, and confident, push into harder, more probing territory; if they've
    been struggling, giving thin answers, or seem to be floundering, ease up slightly — ask something more
    approachable, or break a hard topic into a smaller, more concrete piece — before ramping back up.
- Once questions_answered reaches roughly {MAX_QUESTIONS}, instead of a new question, put a short, honest
  closing assessment here (building on your last feedback) and thank them — no question in that case.

questions_answered:
- A running integer count of how many questions the candidate has GENUINELY answered so far in this entire
  conversation — count every past exchange where they made a real attempt, from the full history above.
  Clarification requests never count, whether past ones or this turn's. On the very first turn, this is 0; if
  this turn is itself a clarification request, this stays the same as it was before this turn (don't count it).
{language_rule}
"""


def _fallback_questions(missing_skills: list, resume_skills: list, jd_title: str) -> list:
    return build_interview_questions(missing_skills or [], resume_skills or [], jd_title or "")[:MAX_QUESTIONS]


def _fallback_reply(conversation: list, missing_skills: list, resume_skills: list, jd_title: str) -> dict:
    questions = _fallback_questions(missing_skills, resume_skills, jd_title)

    if not questions:
        return {
            "feedback": "",
            "question": "I don't have enough detail from your resume or the job description to build questions yet — save an analysis from your dashboard first.",
            "source": "fallback",
            "done": True,
        }

    answered_count = _count_real_answers(conversation)

    if answered_count >= len(questions):
        return {
            "feedback": "",
            "question": "That's the end of this practice session — nice work getting through all the questions. Review the feedback you got along the way, or start a new session for a fresh set.",
            "source": "fallback",
            "done": True,
        }

    current_question = questions[answered_count]["question"]
    last_candidate_message = next((m for m in reversed(conversation) if m.get("role") == "candidate"), None)

    if last_candidate_message and _is_clarification_request(last_candidate_message.get("content", "")):
        # No AI available to actually rephrase it, but the fallback can at least not misread
        # this as a weak answer and skip ahead — repeat the same question and stay put.
        return {
            "feedback": "",
            "question": (
                f"No problem — here's the question again: {current_question} "
                "There's no need for a perfect answer, just walk me through your thinking in your own words."
            ),
            "source": "fallback",
            "done": False,
        }

    feedback = "" if answered_count == 0 else "Thanks for sharing that — without AI feedback configured, I can't critique your specific answer, but here's the next question."
    return {"feedback": feedback, "question": current_question, "source": "fallback", "done": False}


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
    ) + groq_json_instructions(
        '"is_clarification_request" (boolean), "feedback" (string), "question" (string), '
        '"questions_answered" (integer)'
    )

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
    if not all(key in parsed for key in ("is_clarification_request", "feedback", "question", "questions_answered")):
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
        done = parsed["questions_answered"] >= MAX_QUESTIONS
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
            done = parsed["questions_answered"] >= MAX_QUESTIONS

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
