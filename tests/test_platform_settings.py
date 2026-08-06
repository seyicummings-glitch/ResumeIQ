from unittest.mock import Mock
from app.services.platform_settings import is_ai_enabled, get_upload_limits, DEFAULT_ALLOWED_EXTENSIONS, DEFAULT_MAX_UPLOAD_MB


def _db_returning(setting):
    db = Mock()
    db.query.return_value.first.return_value = setting
    return db


def test_is_ai_enabled_true_when_no_settings_row():
    assert is_ai_enabled(_db_returning(None)) is True


def test_is_ai_enabled_reflects_setting_true():
    setting = Mock(ai_suggestions_enabled=True)
    assert is_ai_enabled(_db_returning(setting)) is True


def test_is_ai_enabled_reflects_setting_false():
    setting = Mock(ai_suggestions_enabled=False)
    assert is_ai_enabled(_db_returning(setting)) is False


def test_get_upload_limits_defaults_when_no_settings_row():
    allowed, max_mb = get_upload_limits(_db_returning(None))
    assert allowed == DEFAULT_ALLOWED_EXTENSIONS
    assert max_mb == DEFAULT_MAX_UPLOAD_MB


def test_get_upload_limits_reflects_settings_row():
    setting = Mock(allowed_file_types=".pdf,.docx", max_upload_size_mb=5)
    allowed, max_mb = get_upload_limits(_db_returning(setting))
    assert allowed == {".pdf", ".docx"}
    assert max_mb == 5


def test_get_upload_limits_falls_back_when_allowed_types_empty():
    setting = Mock(allowed_file_types="", max_upload_size_mb=20)
    allowed, max_mb = get_upload_limits(_db_returning(setting))
    assert allowed == DEFAULT_ALLOWED_EXTENSIONS
    assert max_mb == 20
