import pytest
from app.models.models import User
from app.models.ai_conversation_models import AiConversation
from app.routes import ai_conversations as routes


def _user(db_session, **overrides):
    fields = dict(email="jordan@example.com", hashed_password="x", full_name="Jordan Mitchell")
    fields.update(overrides)
    user = User(**fields)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# --- Kind validation --------------------------------------------------------------

def test_unknown_kind_is_rejected(db_session):
    user = _user(db_session)
    with pytest.raises(Exception):
        routes.list_ai_conversations("not_a_real_kind", db=db_session, current_user=user)


# --- History: create / list / get / save / delete ---------------------------------

def test_new_user_has_no_conversation_history(db_session):
    user = _user(db_session)
    result = routes.list_ai_conversations("resume_builder", db=db_session, current_user=user)
    assert result["conversations"] == []


def test_create_starts_an_empty_untitled_conversation(db_session):
    user = _user(db_session)
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)
    assert created["messages"] == []
    assert created["extra"] is None
    assert created["title"] is None
    assert created["id"] is not None


def test_created_conversation_appears_in_history_list(db_session):
    user = _user(db_session)
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)
    result = routes.list_ai_conversations("resume_builder", db=db_session, current_user=user)
    assert [c["id"] for c in result["conversations"]] == [created["id"]]


def test_save_by_id_persists_messages_and_derives_a_title(db_session):
    user = _user(db_session)
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)

    saved = routes.save_ai_conversation_by_id(
        "resume_builder", created["id"],
        routes.SaveConversationInput(messages=[{"role": "user", "content": "Help me build my resume."}]),
        db=db_session, current_user=user,
    )
    assert saved["messages"] == [{"role": "user", "content": "Help me build my resume."}]
    assert saved["title"] == "Help me build my resume."


def test_title_does_not_change_once_set(db_session):
    user = _user(db_session)
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)
    routes.save_ai_conversation_by_id(
        "resume_builder", created["id"],
        routes.SaveConversationInput(messages=[{"role": "user", "content": "First message."}]),
        db=db_session, current_user=user,
    )
    saved_again = routes.save_ai_conversation_by_id(
        "resume_builder", created["id"],
        routes.SaveConversationInput(messages=[
            {"role": "user", "content": "First message."},
            {"role": "assistant", "content": "Reply."},
            {"role": "user", "content": "A completely different second message."},
        ]),
        db=db_session, current_user=user,
    )
    assert saved_again["title"] == "First message."


def test_long_first_message_title_is_truncated(db_session):
    user = _user(db_session)
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)
    long_message = "This is a very long first message that should be truncated for display in the history sidebar list."
    saved = routes.save_ai_conversation_by_id(
        "resume_builder", created["id"],
        routes.SaveConversationInput(messages=[{"role": "user", "content": long_message}]),
        db=db_session, current_user=user,
    )
    assert len(saved["title"]) <= 49
    assert saved["title"].endswith("…")


def test_get_by_id_loads_a_specific_conversation(db_session):
    user = _user(db_session)
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)
    routes.save_ai_conversation_by_id(
        "resume_builder", created["id"],
        routes.SaveConversationInput(messages=[{"role": "user", "content": "Hello."}], extra={"draft": {"title": "x"}}),
        db=db_session, current_user=user,
    )
    loaded = routes.get_ai_conversation_by_id("resume_builder", created["id"], db=db_session, current_user=user)
    assert loaded["messages"] == [{"role": "user", "content": "Hello."}]
    assert loaded["extra"] == {"draft": {"title": "x"}}


def test_multiple_conversations_are_independent(db_session):
    user = _user(db_session)
    first = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)
    second = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)

    routes.save_ai_conversation_by_id(
        "resume_builder", first["id"],
        routes.SaveConversationInput(messages=[{"role": "user", "content": "Conversation one."}]),
        db=db_session, current_user=user,
    )
    routes.save_ai_conversation_by_id(
        "resume_builder", second["id"],
        routes.SaveConversationInput(messages=[{"role": "user", "content": "Conversation two."}]),
        db=db_session, current_user=user,
    )

    loaded_first = routes.get_ai_conversation_by_id("resume_builder", first["id"], db=db_session, current_user=user)
    loaded_second = routes.get_ai_conversation_by_id("resume_builder", second["id"], db=db_session, current_user=user)
    assert loaded_first["title"] == "Conversation one."
    assert loaded_second["title"] == "Conversation two."

    history = routes.list_ai_conversations("resume_builder", db=db_session, current_user=user)
    assert len(history["conversations"]) == 2


def test_history_list_is_ordered_most_recently_updated_first(db_session):
    import datetime

    user = _user(db_session)
    older = AiConversation(user_id=user.id, kind="resume_builder", messages_json=[])
    db_session.add(older)
    db_session.commit()
    newer = AiConversation(user_id=user.id, kind="resume_builder", messages_json=[])
    db_session.add(newer)
    db_session.commit()

    # Set updated_at explicitly rather than relying on real wall-clock timing — the test DB's
    # timestamp resolution is too coarse to reliably separate two inserts a few lines apart.
    # Touching "older" after "newer" was created should sort it first.
    older.updated_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=5)
    db_session.commit()

    history = routes.list_ai_conversations("resume_builder", db=db_session, current_user=user)
    ids_in_order = [c["id"] for c in history["conversations"]]
    assert ids_in_order == [older.id, newer.id]


def test_delete_removes_a_conversation_from_history(db_session):
    user = _user(db_session)
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)
    routes.delete_ai_conversation_by_id("resume_builder", created["id"], db=db_session, current_user=user)

    history = routes.list_ai_conversations("resume_builder", db=db_session, current_user=user)
    assert history["conversations"] == []


def test_get_by_id_404s_for_another_users_conversation(db_session):
    owner = _user(db_session, email="owner@example.com")
    other = _user(db_session, email="other@example.com")
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=owner)

    with pytest.raises(Exception):
        routes.get_ai_conversation_by_id("resume_builder", created["id"], db=db_session, current_user=other)


def test_get_by_id_404s_for_wrong_kind(db_session):
    user = _user(db_session)
    created = routes.create_ai_conversation("resume_builder", db=db_session, current_user=user)
    with pytest.raises(Exception):
        routes.get_ai_conversation_by_id("career_coach", created["id"], db=db_session, current_user=user)


# --- Legacy single-conversation endpoints (Career Coach) still behave the same --------

def test_legacy_get_returns_empty_conversation_when_none_saved(db_session):
    user = _user(db_session)
    result = routes.get_ai_conversation("career_coach", db=db_session, current_user=user)
    assert result == {"messages": [], "extra": None, "updated_at": None}


def test_legacy_put_then_get_round_trips(db_session):
    user = _user(db_session)
    routes.save_ai_conversation(
        "career_coach", routes.SaveConversationInput(messages=[{"role": "user", "content": "Hi."}], extra={"topic": "salary"}),
        db=db_session, current_user=user,
    )
    result = routes.get_ai_conversation("career_coach", db=db_session, current_user=user)
    assert result["messages"] == [{"role": "user", "content": "Hi."}]
    assert result["extra"] == {"topic": "salary"}


def test_legacy_get_resolves_to_most_recently_updated_row(db_session):
    """Once a kind can have multiple rows (only resume_builder does in practice), the legacy
    single-conversation endpoints must still resolve deterministically rather than picking an
    arbitrary row."""
    user = _user(db_session)
    older = AiConversation(user_id=user.id, kind="resume_builder", messages_json=[{"role": "user", "content": "old"}])
    db_session.add(older)
    db_session.commit()

    newer = AiConversation(user_id=user.id, kind="resume_builder", messages_json=[{"role": "user", "content": "new"}])
    db_session.add(newer)
    db_session.commit()

    result = routes.get_ai_conversation("resume_builder", db=db_session, current_user=user)
    assert result["messages"] == [{"role": "user", "content": "new"}]


def test_legacy_delete_clears_conversation(db_session):
    user = _user(db_session)
    routes.save_ai_conversation(
        "career_coach", routes.SaveConversationInput(messages=[{"role": "user", "content": "Hi."}]),
        db=db_session, current_user=user,
    )
    routes.clear_ai_conversation("career_coach", db=db_session, current_user=user)
    result = routes.get_ai_conversation("career_coach", db=db_session, current_user=user)
    assert result == {"messages": [], "extra": None, "updated_at": None}
