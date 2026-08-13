from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class AiConversation(Base):
    """Persists an AI conversation (messages plus any feature-specific extra state, e.g. the AI
    Resume Builder's draft) so it survives a page reload, a closed browser tab, or logging in
    from a different device — the same account should see the same conversations everywhere, not
    just in whichever browser they were started in.

    A user can have multiple conversations of the same `kind` — the AI Resume Builder supports a
    ChatGPT-style "New Chat" plus a history list to switch back to any past conversation, each
    with its own messages and draft. Career Coach doesn't (yet) expose that UI and only ever
    keeps one conversation per (user, kind), but the data model no longer enforces that as a
    uniqueness constraint — it's just a convention that kind's frontend happens to follow."""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String, nullable=False)  # "resume_builder" | "career_coach"
    # Auto-derived from the first user message (see _derive_title in app/routes/ai_conversations.py)
    # the same way ChatGPT-style history sidebars title a conversation — None until there's a
    # first message to derive it from.
    title = Column(String, nullable=True)
    messages_json = Column(JSON, nullable=False, default=list)
    extra_json = Column(JSON, nullable=True)  # kind-specific extra state (draft, jd context, focused topic, ...)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
