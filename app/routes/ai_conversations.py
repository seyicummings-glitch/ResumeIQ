from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any

from app.database import get_db
from app.models.models import User
from app.models.ai_conversation_models import AiConversation
from app.security import get_current_user

router = APIRouter(prefix="/ai-conversations", tags=["AI Conversations"])

# Kept short and explicit rather than open-ended — anything persisted here needs a frontend
# feature that actually reads it back (see ResumeBuilderDraftContext / CareerCoachContext).
ALLOWED_KINDS = {"resume_builder", "career_coach"}


def _validate_kind(kind: str) -> None:
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=404, detail=f"Unknown conversation kind '{kind}'.")


@router.get("/{kind}")
def get_ai_conversation(
    kind: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Loads the saved conversation for this user, so opening the AI Resume Builder or the
    Career Coach on a new device/browser picks up right where they left off, instead of
    starting blank. Returns an empty conversation (not a 404) when nothing's been saved yet —
    that's the normal state for a user who's never used this feature."""
    _validate_kind(kind)
    row = (
        db.query(AiConversation)
        .filter(AiConversation.user_id == current_user.id, AiConversation.kind == kind)
        .first()
    )
    if not row:
        return {"messages": [], "extra": None, "updated_at": None}
    return {"messages": row.messages_json or [], "extra": row.extra_json, "updated_at": row.updated_at}


class SaveConversationInput(BaseModel):
    messages: list[dict[str, Any]] = []
    extra: dict[str, Any] | None = None


@router.put("/{kind}")
def save_ai_conversation(
    kind: str,
    data: SaveConversationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upserts the full current state of this conversation — called by the frontend after
    every turn (and after any change to feature-specific extra state, like the Resume
    Builder's draft) so the server always has the latest version, not just whatever was true
    at the end of the session."""
    _validate_kind(kind)
    row = (
        db.query(AiConversation)
        .filter(AiConversation.user_id == current_user.id, AiConversation.kind == kind)
        .first()
    )
    if row:
        row.messages_json = data.messages
        row.extra_json = data.extra
    else:
        row = AiConversation(
            user_id=current_user.id, kind=kind, messages_json=data.messages, extra_json=data.extra
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return {"messages": row.messages_json or [], "extra": row.extra_json, "updated_at": row.updated_at}


@router.delete("/{kind}")
def clear_ai_conversation(
    kind: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explicitly clears a saved conversation — e.g. the user starting fresh on purpose."""
    _validate_kind(kind)
    db.query(AiConversation).filter(
        AiConversation.user_id == current_user.id, AiConversation.kind == kind
    ).delete()
    db.commit()
    return {"message": "Conversation cleared."}
