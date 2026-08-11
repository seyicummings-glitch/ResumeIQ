import pytest
from pydantic import ValidationError

from app.schemas import UserCreate, PasswordChange, PasswordResetConfirm, UserLogin, validate_password_strength


def test_validate_password_strength_accepts_compliant_password():
    assert validate_password_strength("Passw0rd!") == "Passw0rd!"


@pytest.mark.parametrize("password,expected_fragment", [
    ("Sh0rt!", "at least 8 characters"),
    ("A" * 18 + "b1!", "at most 20 characters"),  # 21 chars total -- one over the max
    ("nouppercase1!", "uppercase"),
    ("NOLOWERCASE1!", "lowercase"),
    ("NoNumbersHere!", "number"),
    ("NoSpecialChar123", "special character"),
])
def test_validate_password_strength_rejects_each_rule_violation(password, expected_fragment):
    with pytest.raises(ValueError, match=expected_fragment):
        validate_password_strength(password)


def test_user_create_rejects_weak_password():
    with pytest.raises(ValidationError):
        UserCreate(email="test@example.com", password="weak", full_name="Test")


def test_user_create_accepts_strong_password():
    user = UserCreate(email="test@example.com", password="Passw0rd!", full_name="Test")
    assert user.password == "Passw0rd!"


def test_password_change_rejects_weak_new_password():
    with pytest.raises(ValidationError):
        PasswordChange(current_password="whatever-it-was", new_password="weak")


def test_password_reset_confirm_rejects_weak_new_password():
    with pytest.raises(ValidationError):
        PasswordResetConfirm(token="abc", new_password="weak")


def test_user_login_does_not_enforce_password_strength():
    """Login must never reject an existing account's real password just
    because it predates this policy -- only new-password fields are validated."""
    login = UserLogin(email="test@example.com", password="anything-goes-here")
    assert login.password == "anything-goes-here"

    login2 = UserLogin(email="test@example.com", password="x")
    assert login2.password == "x"
