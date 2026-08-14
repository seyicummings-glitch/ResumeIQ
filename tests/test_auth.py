import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.models import User, PendingRegistration
from app.routes import auth as routes
from app.schemas import (
    UserCreate,
    UserLogin,
    UserUpdate,
    PasswordResetRequest,
    EmailVerificationConfirm,
)
from app.security import normalize_email, create_email_verification_token


def _register_and_verify(db_session, email, password="Pass1234!", full_name="Test"):
    """Helper mirroring what a real user does: register (creates a pending
    registration, not a User), then click the emailed link (creates the User).
    Returns the resulting User row."""
    routes.register(UserCreate(email=email, password=password, full_name=full_name), db_session)
    token = create_email_verification_token(normalize_email(email))
    routes.verify_email(EmailVerificationConfirm(token=token), db_session)
    return db_session.query(User).filter(User.email == normalize_email(email)).first()


def test_normalize_email_lowercases_and_strips():
    assert normalize_email("  Test@Example.COM  ") == "test@example.com"


def test_register_creates_pending_registration_not_a_user(db_session):
    routes.register(UserCreate(email="Test@Example.com", password="Pass1234!", full_name="Test"), db_session)

    assert db_session.query(User).count() == 0
    pending = db_session.query(PendingRegistration).filter(PendingRegistration.email == "test@example.com").first()
    assert pending is not None
    assert pending.full_name == "Test"


def test_register_overwrites_existing_pending_registration_for_same_email(db_session):
    routes.register(UserCreate(email="test@example.com", password="First1234!", full_name="First"), db_session)
    routes.register(UserCreate(email="test@example.com", password="Second1234!", full_name="Second"), db_session)

    rows = db_session.query(PendingRegistration).filter(PendingRegistration.email == "test@example.com").all()
    assert len(rows) == 1
    assert rows[0].full_name == "Second"


def test_login_rejected_before_email_is_verified(db_session):
    routes.register(UserCreate(email="test@example.com", password="Pass1234!", full_name="Test"), db_session)

    # No User row exists yet — this is "wrong credentials," not "unverified."
    with pytest.raises(HTTPException) as exc_info:
        routes.login(UserLogin(email="test@example.com", password="Pass1234!"), db_session)
    assert exc_info.value.status_code == 401


def test_verify_email_creates_the_lowercased_user(db_session):
    user = _register_and_verify(db_session, "Test@Example.com")
    assert user.email == "test@example.com"
    assert user.is_verified is True


def test_verify_email_rejects_invalid_token(db_session):
    with pytest.raises(HTTPException) as exc_info:
        routes.verify_email(EmailVerificationConfirm(token="not-a-real-token"), db_session)
    assert exc_info.value.status_code == 400


def test_verify_email_rejects_token_with_no_matching_pending_registration(db_session):
    token = create_email_verification_token("never-registered@example.com")
    with pytest.raises(HTTPException) as exc_info:
        routes.verify_email(EmailVerificationConfirm(token=token), db_session)
    assert exc_info.value.status_code == 400


def test_verify_email_is_idempotent(db_session):
    _register_and_verify(db_session, "test@example.com")
    token = create_email_verification_token("test@example.com")

    result = routes.verify_email(EmailVerificationConfirm(token=token), db_session)
    assert "verified" in result["message"].lower()
    assert db_session.query(User).filter(User.email == "test@example.com").count() == 1


def test_verify_email_grants_free_signup_tokens(db_session):
    from app.services.feature_gate import get_credit_balance

    user = _register_and_verify(db_session, "new@example.com")
    assert get_credit_balance(db_session, user.id) == 100  # DEFAULT_FREE_SIGNUP_CREDITS


def test_verify_email_grants_admin_configured_signup_tokens(db_session):
    from app.models.admin_models import AppSetting
    from app.services.feature_gate import get_credit_balance

    db_session.add(AppSetting(free_signup_credits=250))
    db_session.commit()

    user = _register_and_verify(db_session, "new2@example.com")
    assert get_credit_balance(db_session, user.id) == 250


def test_register_rejects_case_variant_of_existing_verified_email(db_session):
    _register_and_verify(db_session, "test@example.com", full_name="First")

    with pytest.raises(HTTPException) as exc_info:
        routes.register(UserCreate(email="TEST@EXAMPLE.COM", password="Pass1234!", full_name="Second"), db_session)
    assert exc_info.value.status_code == 400

    assert db_session.query(User).filter(User.email == "test@example.com").count() == 1


def test_register_rejects_disposable_email():
    with pytest.raises(ValidationError):
        UserCreate(email="test@mailinator.com", password="Pass1234!", full_name="Test")


def test_register_rejects_undeliverable_domain(monkeypatch):
    import app.schemas as schemas_module
    from email_validator import EmailNotValidError

    def _fake_check(*args, **kwargs):
        raise EmailNotValidError("no MX records")

    monkeypatch.setattr(schemas_module, "check_email_deliverable", _fake_check)

    with pytest.raises(ValidationError):
        UserCreate(email="test@nonexistent-domain-xyz.com", password="Pass1234!", full_name="Test")


def test_login_succeeds_regardless_of_case(db_session):
    _register_and_verify(db_session, "test@example.com")

    token = routes.login(UserLogin(email="Test@Example.com", password="Pass1234!"), db_session)
    assert "access_token" in token


def test_update_me_rejects_case_variant_collision(db_session):
    _register_and_verify(db_session, "taken@example.com", full_name="Taken")
    me = _register_and_verify(db_session, "me@example.com", full_name="Me")

    with pytest.raises(HTTPException) as exc_info:
        routes.update_me(UserUpdate(email="TAKEN@EXAMPLE.COM"), db_session, me)
    assert exc_info.value.status_code == 400


def test_update_me_stores_new_email_lowercased(db_session):
    me = _register_and_verify(db_session, "me@example.com", full_name="Me")

    updated = routes.update_me(UserUpdate(email="New@Example.com"), db_session, me)
    assert updated.email == "new@example.com"


def test_password_reset_request_finds_user_case_insensitively(db_session, monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    _register_and_verify(db_session, "test@example.com")

    result = routes.request_password_reset(PasswordResetRequest(email="TEST@EXAMPLE.COM"), db_session)
    assert "reset_token" in result  # dev fallback only includes this when a real user was found
