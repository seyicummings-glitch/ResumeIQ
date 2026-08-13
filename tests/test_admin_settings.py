import pytest

from app.models.models import User
from app.routes import admin as routes


def _admin(db_session):
    user = User(email="admin@example.com", hashed_password="x", role="admin")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_get_settings_creates_row_with_token_economy_defaults(db_session):
    admin = _admin(db_session)
    result = routes.get_settings(db_session, admin)
    assert result["freeSignupCredits"] == 100
    assert result["freeCreditRefreshHours"] == 720


def test_update_settings_changes_free_signup_credits(db_session):
    admin = _admin(db_session)
    result = routes.update_settings(routes.SettingsUpdateInput(freeSignupCredits=250), db_session, admin)
    assert result["freeSignupCredits"] == 250


def test_update_settings_changes_refresh_hours(db_session):
    admin = _admin(db_session)
    result = routes.update_settings(routes.SettingsUpdateInput(freeCreditRefreshHours=24), db_session, admin)
    assert result["freeCreditRefreshHours"] == 24


def test_update_settings_rejects_negative_free_signup_credits(db_session):
    admin = _admin(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.update_settings(routes.SettingsUpdateInput(freeSignupCredits=-5), db_session, admin)
    assert exc_info.value.status_code == 400


def test_update_settings_rejects_non_positive_refresh_hours(db_session):
    admin = _admin(db_session)
    with pytest.raises(Exception) as exc_info:
        routes.update_settings(routes.SettingsUpdateInput(freeCreditRefreshHours=0), db_session, admin)
    assert exc_info.value.status_code == 400


def test_update_settings_leaves_unspecified_fields_unchanged(db_session):
    admin = _admin(db_session)
    routes.update_settings(routes.SettingsUpdateInput(freeSignupCredits=300), db_session, admin)
    result = routes.update_settings(routes.SettingsUpdateInput(supportEmail="help@example.com"), db_session, admin)
    assert result["freeSignupCredits"] == 300
    assert result["supportEmail"] == "help@example.com"
