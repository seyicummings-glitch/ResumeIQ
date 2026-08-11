from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class AiConversation(Base):
    """Persists an in-progress AI conversation (messages plus any feature-specific extra state,
    e.g. the AI Resume Builder's draft) so it survives a page reload, a closed browser tab, or
    logging in from a different device — the same account should see the same conversation
    everywhere, not just in whichever browser it was started in. One row per (user, kind):
    saved by upserting on every turn rather than growing a new row per message, matching how
    the frontend already treats each of these as a single evolving session, not a log."""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String, nullable=False)  # "resume_builder" | "career_coach"
    messages_json = Column(JSON, nullable=False, default=list)
    extra_json = Column(JSON, nullable=True)  # kind-specific extra state (draft, jd context, focused topic, ...)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "kind", name="uq_ai_conversation_user_kind"),
    )
