from unittest.mock import patch, Mock
from app.services.email_service import is_email_configured, send_password_reset_email


def test_not_configured_when_missing_all(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    assert is_email_configured() is False


def test_not_configured_when_partially_set(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    assert is_email_configured() is False


def test_configured_when_all_set(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    assert is_email_configured() is True


@patch("app.services.email_service.smtplib.SMTP")
def test_send_password_reset_email_builds_link_and_sends(mock_smtp_cls, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com")

    mock_server = Mock()
    mock_smtp_cls.return_value.__enter__ = Mock(return_value=mock_server)
    mock_smtp_cls.return_value.__exit__ = Mock(return_value=False)

    send_password_reset_email("someone@example.com", "abc123")

    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user@example.com", "app-password")
    assert mock_server.send_message.call_count == 1
    sent_message = mock_server.send_message.call_args[0][0]
    assert sent_message["To"] == "someone@example.com"
    assert "https://app.example.com/reset-password?token=abc123" in sent_message.get_content()
