import pytest
from fastapi import HTTPException

from app.models.models import User
from app.routes import auth as routes
from app.schemas import UserCreate, UserLogin, UserUpdate, PasswordResetRequest
from app.security import normalize_email


def test_normalize_email_lowercases_and_strips():
    assert normalize_email("  Test@Example.COM  ") == "test@example.com"


def test_register_lowercases_stored_email(db_session):
    result = routes.register(UserCreate(email="Test@Example.com", password="Pass1234!", full_name="Test"), db_session)
    assert result.email == "test@example.com"


def test_register_rejects_case_variant_of_existing_email(db_session):
    routes.register(UserCreate(email="test@example.com", password="Pass1234!", full_name="First"), db_session)

    with pytest.raises(HTTPException) as exc_info:
        routes.register(UserCreate(email="TEST@EXAMPLE.COM", password="Pass1234!", full_name="Second"), db_session)
    assert exc_info.value.status_code == 400

    assert db_session.query(User).filter(User.email == "test@example.com").count() == 1


def test_login_succeeds_regardless_of_case(db_session):
    routes.register(UserCreate(email="test@example.com", password="Pass1234!", full_name="Test"), db_session)

    token = routes.login(UserLogin(email="Test@Example.com", password="Pass1234!"), db_session)
    assert "access_token" in token


def test_update_me_rejects_case_variant_collision(db_session):
    routes.register(UserCreate(email="taken@example.com", password="Pass1234!", full_name="Taken"), db_session)
    me = routes.register(UserCreate(email="me@example.com", password="Pass1234!", full_name="Me"), db_session)

    with pytest.raises(HTTPException) as exc_info:
        routes.update_me(UserUpdate(email="TAKEN@EXAMPLE.COM"), db_session, me)
    assert exc_info.value.status_code == 400


def test_update_me_stores_new_email_lowercased(db_session):
    me = routes.register(UserCreate(email="me@example.com", password="Pass1234!", full_name="Me"), db_session)

    updated = routes.update_me(UserUpdate(email="New@Example.com"), db_session, me)
    assert updated.email == "new@example.com"


def test_password_reset_request_finds_user_case_insensitively(db_session, monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    routes.register(UserCreate(email="test@example.com", password="Pass1234!", full_name="Test"), db_session)

    result = routes.request_password_reset(PasswordResetRequest(email="TEST@EXAMPLE.COM"), db_session)
    assert "reset_token" in result  # dev fallback only includes this when a real user was found
