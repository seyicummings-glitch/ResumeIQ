"""
Conversational AI Career Coach — the one persistent AI presence available from anywhere in
the app, not scoped to a single feature. Follows the same shape as ai_interviewer.py /
resume_builder.py: Gemini SDK, module-level MODEL constant, a GEMINI_API_KEY gate, a
Gemini -> Gemini(2nd key) -> Groq cascade, and a plain-text fallback reply when no AI is
available (there's no rule-based equivalent for open-ended coaching).

Grounded in the user's whole career context (see app/services/career_context.py) — their
resume, target role, skill gaps, roadmap progress, and how their last skill assessment and
mock interview went — so it can answer with real specifics ("your ATS score was 62 because…")
instead of generic career advice. Optionally scoped further to a specific roadmap topic when
the user asks about one directly.

The AI Resume Builder and Interview Practice remain their own specialized, structured flows
(a draft-editing UI and a turn-by-turn scored assessment respectively need their own shape) —
this coach is the general-purpose "ask me anything, anytime" layer that sits alongside them and
knows about their results, rather than replacing them.
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


COACH_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
    },
    "required": ["reply"],
    "additionalProperties": False,
}


def _build_system_prompt(context: dict, topic_context: str | None) -> str:
    role_label = context.get("target_role") or "their target role"
    industry_label = f" in {context['industry']}" if context.get("industry") else ""

    context_blocks = []
    if context.get("resume_text"):
        context_blocks.append(f"Their saved resume:\n{context['resume_text'][:3000]}")
    if context.get("resume_skills"):
        context_blocks.append(f"Skills on their resume: {', '.join(context['resume_skills'])}")
    if context.get("jd_title") or context.get("jd_content"):
        jd_label = context.get("jd_title") or "a target job"
        context_blocks.append(f"Their most recent job match target ({jd_label}):\n{(context.get('jd_content') or '')[:2000]}")
    if context.get("missing_skills"):
        context_blocks.append(f"Skill gaps identified against that job: {', '.join(context['missing_skills'][:10])}")
    if context.get("roadmap_summary"):
        context_blocks.append(f"Their current learning roadmap:\n{context['roadmap_summary']}")
    if context.get("skill_assessment_summary"):
        context_blocks.append(f"Latest skill assessment results:\n{context['skill_assessment_summary']}")
    if context.get("interview_summary"):
        context_blocks.append(f"Latest mock interview feedback:\n{context['interview_summary']}")

    known_context = "\n\n".join(context_blocks) if context_blocks else "(Nothing on record yet — they're just getting started.)"

    topic_block = (
        f"\n\nThey're currently focused on this specific roadmap topic — ground your answer in it "
        f"whenever relevant:\n{topic_context}"
        if topic_context
        else ""
    )

    return f"""You are the AI Career Coach inside ResumeIQ — the one persistent AI assistant available from
anywhere in the app, helping this person become job-ready as {role_label}{industry_label}. This is a real,
ongoing conversation: remember what's been said earlier in this session and build on it rather than repeating
yourself or re-asking for things you already know from their account below.

What you already know about them from their account:
{known_context}
{topic_block}

What you can help with:
- Answer questions and explain concepts clearly, at the right depth for someone learning them for the first
  time — plain language and concrete examples before jargon.
- Give personalized career guidance grounded in what's actually in their account above — e.g. what to
  prioritize next, how a skill gap connects to the job they're targeting, how to talk about a career change,
  or how to interpret a score they got elsewhere in the app (resume analysis, skill assessment, mock
  interview).
- Generate a small, specific practice task when asked (a coding kata, a short written exercise, a scenario to
  reason through) — sized to be doable in one sitting.
- Review work they paste in (code, a resume bullet, a written answer) and give specific, honest feedback:
  what's correct, what's wrong or weak, and a concrete suggestion to improve it — like a mentor doing review,
  not empty praise.
- Point them to the right place in the app for structured work — the AI Resume Builder for actually
  drafting/editing their resume, Interview Practice for a full scored mock interview, Skill Assessment for a
  graded quiz — when that's a better fit than answering inline.

Rules:
- Be direct and specific — reference what they actually asked, pasted, or already have on record above, never
  generic filler advice.
- If reviewing work, be honest about real problems; don't just validate everything as good.
- Never fabricate facts about them beyond what's given above or said in this conversation — if you don't have
  enough information to answer well, ask a clarifying question rather than guessing.
- Keep replies focused and conversational — typically a few sentences to a short paragraph; longer only when
  walking through code, a worked example, or a multi-step explanation genuinely requires it.
"""


def _fallback_reply() -> dict:
    return {
        "reply": (
            "The AI Career Coach isn't available right now — the AI service isn't configured or has hit its "
            "usage limit. The rest of the platform (resume builder, roadmap, interview practice) still works."
        ),
        "source": "fallback",
    }


def _coach_reply_via_groq(conversation: list[dict], context: dict, topic_context: str | None) -> dict:
    """Groq equivalent of the Gemini call in get_coach_reply — same system prompt (reuses
    _build_system_prompt exactly) and conversation history, adapted only in transport
    (Gemini's role/parts format vs. OpenAI-style messages) and how the JSON shape is
    requested/parsed."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    system_prompt = _build_system_prompt(context, topic_context) + groq_json_instructions('"reply" (string)')

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": "assistant" if m["role"] == "coach" else "user", "content": m["content"]} for m in conversation
    )

    client = groq_client(api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(response.choices[0].message.content)
    if "reply" not in parsed:
        raise ValueError("Groq response missing required key: reply")
    return parsed


def _try_groq_coach_reply(conversation: list[dict], context: dict, topic_context: str | None) -> dict | None:
    """Never raises — returns None on any failure so the caller can fall through
    to the plain-text fallback instead of surfacing an error."""
    try:
        parsed = _coach_reply_via_groq(conversation, context, topic_context)
        logger.info("career_coach_ai.get_coach_reply served by groq (gemini quota/rate-limit hit)")
        return {"reply": parsed["reply"], "source": "ai"}
    except Exception:
        logger.warning("career_coach_ai.get_coach_reply: groq fallback also failed", exc_info=True)
        return None


def get_coach_reply(
    conversation: list[dict],
    context: dict | None = None,
    topic_context: str | None = None,
    ai_enabled: bool = True,
) -> dict:
    """conversation is a list of {"role": "user"|"coach", "content": str}, in chronological
    order, including the message being replied to. context is the dict returned by
    career_context.get_user_career_context (or {} if unavailable). Falls back to a plain
    unavailability message if AI features have been disabled platform-wide (ai_enabled=False,
    set via Admin Settings) or no server-wide GEMINI_API_KEY is configured — there's no
    rule-based tutor to fall back to."""
    context = context or {}

    if not ai_enabled:
        return _fallback_reply()

    gemini_keys = _gemini_api_keys()
    if not gemini_keys:
        return _fallback_reply()

    for api_key in gemini_keys:
        try:
            client = _client(api_key)
            contents = [
                {"role": "model" if m["role"] == "coach" else "user", "parts": [{"text": m["content"]}]}
                for m in conversation
            ]
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=3000,
                    thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"),
                    system_instruction=_build_system_prompt(context, topic_context),
                    response_mime_type="application/json",
                    response_json_schema=COACH_SCHEMA,
                ),
            )
            parsed = json.loads(response.text)
            logger.info("career_coach_ai.get_coach_reply served by gemini")
            return {"reply": parsed["reply"], "source": "ai"}
        except genai_errors.ClientError as e:
            if e.code == 429:
                continue  # try the next configured Gemini key, if any
            logger.info("career_coach_ai.get_coach_reply served by fallback (gemini ClientError, code=%s)", e.code)
            return _fallback_reply()
        except genai_errors.ServerError:
            logger.info("career_coach_ai.get_coach_reply served by fallback (gemini ServerError)")
            return _fallback_reply()
        except Exception:
            logger.info("career_coach_ai.get_coach_reply served by fallback (unexpected gemini error)")
            return _fallback_reply()

    # Every configured Gemini key hit a 429 — try Groq before giving up.
    groq_result = _try_groq_coach_reply(conversation, context, topic_context)
    if groq_result is not None:
        return groq_result
    logger.info("career_coach_ai.get_coach_reply served by fallback (all gemini keys quota/rate-limited)")
    return _fallback_reply()
