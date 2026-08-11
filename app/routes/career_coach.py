from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.security import get_current_user
from app.services.platform_settings import is_ai_enabled
from app.services.career_context import get_user_career_context, find_roadmap_topic, topic_context_text
from app.services.career_coach_ai import get_coach_reply

router = APIRouter(prefix="/career-coach", tags=["Career Coach"])


class CoachChatMessage(BaseModel):
    role: str  # "user" | "coach"
    content: str


class CoachChatInput(BaseModel):
    conversation: list[CoachChatMessage] = []
    topic_key: str | None = None


@router.post("/chat")
def post_career_coach_chat(
    data: CoachChatInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """One turn of the AI Career Coach chat — the single persistent AI assistant available
    from anywhere in the app. The frontend keeps the running conversation client-side and
    resends it in full each turn, same pattern as /interview/chat and /resume-builder/chat.
    Always grounded in the user's whole career context (resume, target role, skill gaps,
    roadmap, latest skill assessment and mock interview) via career_context.py, so it can
    answer specifically instead of generically — no matter which page it was opened from.
    Optionally scoped further to a specific roadmap topic (topic_key)."""
    if not data.conversation:
        raise HTTPException(status_code=400, detail="conversation must include at least one message.")

    context = get_user_career_context(db, current_user)
    topic = find_roadmap_topic(context["roadmap"], data.topic_key)

    result = get_coach_reply(
        conversation=[m.model_dump() for m in data.conversation],
        context=context,
        topic_context=topic_context_text(topic) if topic else None,
        ai_enabled=is_ai_enabled(db),
    )

    return result
