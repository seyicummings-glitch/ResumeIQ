from unittest.mock import patch, Mock
import pytest
from app.services.github_analyzer import (
    extract_username_from_input,
    extract_languages_used,
    analyze_github_profile,
)


def test_extract_username_from_plain_username():
    assert extract_username_from_input("octocat") == "octocat"


def test_extract_username_from_url():
    assert extract_username_from_input("https://github.com/octocat") == "octocat"


def test_extract_languages_used_dedupes_and_sorts():
    repos = [{"language": "Python"}, {"language": "JavaScript"}, {"language": "Python"}, {"language": None}]
    assert extract_languages_used(repos) == ["JavaScript", "Python"]


@patch("app.services.github_analyzer.requests.get")
def test_analyze_github_profile_not_found(mock_get):
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    with pytest.raises(ValueError):
        analyze_github_profile("nonexistent-user-xyz")
