from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Any

from app.database import get_db
from app.models.models import User
from app.models.ai_conversation_models import AiConversation
from app.security import get_current_user

router = APIRouter(prefix="/ai-conversations", tags=["AI Conversations"])

# Kept short and explicit rather than open-ended — anything persisted here needs a frontend
# feature that actually reads it back (see ResumeBuilderDraftContext / CareerCoachContext).
ALLOWED_KINDS = {"resume_builder", "career_coach"}

_TITLE_MAX_LENGTH = 48


def _validate_kind(kind: str) -> None:
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=404, detail=f"Unknown conversation kind '{kind}'.")


def _derive_title(messages: list[dict]) -> str | None:
    """Auto-titles a conversation from its first user message, the same way ChatGPT-style
    history sidebars do, without a separate naming call. Returns None when there's nothing to
    title yet (a brand new, empty conversation) — callers show a "New conversation" placeholder
    for that themselves rather than persisting one."""
    for message in messages:
        content = (message.get("content") or "").strip() if message.get("role") == "user" else ""
        if content:
            single_line = " ".join(content.split())
            return single_line[:_TITLE_MAX_LENGTH] + ("…" if len(single_line) > _TITLE_MAX_LENGTH else "")
    return None


def _effective_title(row: AiConversation) -> str | None:
    """Prefers the persisted title, but falls back to deriving one on the fly — covers rows
    saved before titling existed, or a row whose title was never (re)computed for any reason,
    without needing a backfill migration."""
    return row.title or _derive_title(row.messages_json or [])


def _row_to_conversation(row: AiConversation) -> dict:
    return {
        "id": row.id,
        "messages": row.messages_json or [],
        "extra": row.extra_json,
        "title": _effective_title(row),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _row_to_summary(row: AiConversation) -> dict:
    return {"id": row.id, "title": _effective_title(row), "created_at": row.created_at, "updated_at": row.updated_at}


def _get_owned_conversation(db: Session, current_user: User, kind: str, conversation_id: int) -> AiConversation:
    row = (
        db.query(AiConversation)
        .filter(
            AiConversation.id == conversation_id,
            AiConversation.user_id == current_user.id,
            AiConversation.kind == kind,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return row


class SaveConversationInput(BaseModel):
    messages: list[dict[str, Any]] = []
    extra: dict[str, Any] | None = None


# --- Legacy single-conversation endpoints ------------------------------------------------------
# Used by Career Coach, which has no history UI and only ever keeps one conversation per (user,
# kind). Resolves to the most-recently-updated conversation of this kind, for backward
# compatibility now that a kind (Resume Builder) can have more than one — functionally identical
# to before for any kind that only ever has a single row, which Career Coach still does.

@router.get("/{kind}")
def get_ai_conversation(
    kind: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Loads the saved conversation for this user, so opening the Career Coach on a new
    device/browser picks up right where they left off, instead of starting blank. Returns an
    empty conversation (not a 404) when nothing's been saved yet — that's the normal state for a
    user who's never used this feature."""
    _validate_kind(kind)
    row = (
        db.query(AiConversation)
        .filter(AiConversation.user_id == current_user.id, AiConversation.kind == kind)
        .order_by(desc(AiConversation.updated_at), desc(AiConversation.id))
        .first()
    )
    if not row:
        return {"messages": [], "extra": None, "updated_at": None}
    return {"messages": row.messages_json or [], "extra": row.extra_json, "updated_at": row.updated_at}


@router.put("/{kind}")
def save_ai_conversation(
    kind: str,
    data: SaveConversationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upserts the full current state of this conversation — called by the frontend after
    every turn (and after any change to feature-specific extra state, like the focused topic)
    so the server always has the latest version, not just whatever was true at the end of the
    session."""
    _validate_kind(kind)
    row = (
        db.query(AiConversation)
        .filter(AiConversation.user_id == current_user.id, AiConversation.kind == kind)
        .order_by(desc(AiConversation.updated_at), desc(AiConversation.id))
        .first()
    )
    if row:
        row.messages_json = data.messages
        row.extra_json = data.extra
        if not row.title:
            row.title = _derive_title(data.messages)
    else:
        row = AiConversation(
            user_id=current_user.id, kind=kind, messages_json=data.messages, extra_json=data.extra,
            title=_derive_title(data.messages),
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


# --- History endpoints --------------------------------------------------------------------------
# Multiple conversations per (user, kind) — a "New Chat" button plus a list to switch back to any
# past conversation, each with its own messages and extra state (e.g. the Resume Builder's
# draft). Currently only used by the AI Resume Builder's frontend.

@router.get("/{kind}/history")
def list_ai_conversations(
    kind: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All of this user's conversations of this kind, most recently updated first — powers the
    history sidebar."""
    _validate_kind(kind)
    rows = (
        db.query(AiConversation)
        .filter(AiConversation.user_id == current_user.id, AiConversation.kind == kind)
        .order_by(desc(AiConversation.updated_at), desc(AiConversation.id))
        .all()
    )
    return {"conversations": [_row_to_summary(row) for row in rows]}


@router.post("/{kind}/history")
def create_ai_conversation(
    kind: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Starts a brand new, empty conversation of this kind — the "New Chat" action."""
    _validate_kind(kind)
    row = AiConversation(user_id=current_user.id, kind=kind, messages_json=[], extra_json=None, title=None)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_conversation(row)


@router.get("/{kind}/history/{conversation_id}")
def get_ai_conversation_by_id(
    kind: str,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Loads one specific past conversation — clicking into it from the history list."""
    _validate_kind(kind)
    row = _get_owned_conversation(db, current_user, kind, conversation_id)
    return _row_to_conversation(row)


@router.put("/{kind}/history/{conversation_id}")
def save_ai_conversation_by_id(
    kind: str,
    conversation_id: int,
    data: SaveConversationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Saves the full current state of one specific conversation by id — the frontend's autosave
    once it knows which conversation in the history it's actively editing."""
    _validate_kind(kind)
    row = _get_owned_conversation(db, current_user, kind, conversation_id)
    row.messages_json = data.messages
    row.extra_json = data.extra
    if not row.title:
        row.title = _derive_title(data.messages)
    db.commit()
    db.refresh(row)
    return _row_to_conversation(row)


@router.delete("/{kind}/history/{conversation_id}")
def delete_ai_conversation_by_id(
    kind: str,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Removes one specific conversation from the history list."""
    _validate_kind(kind)
    row = _get_owned_conversation(db, current_user, kind, conversation_id)
    db.delete(row)
    db.commit()
    return {"message": "Conversation deleted."}
