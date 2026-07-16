import requests
import re

GITHUB_API_BASE = "https://api.github.com"


def extract_username_from_input(input_str: str) -> str:
    """Accepts either a plain username or a full GitHub profile URL."""
    input_str = input_str.strip()
    match = re.search(r"github\.com/([A-Za-z0-9-]+)", input_str)
    if match:
        return match.group(1)
    return input_str


def fetch_github_profile(username: str) -> dict:
    url = f"{GITHUB_API_BASE}/users/{username}"
    response = requests.get(url, timeout=10)

    if response.status_code == 404:
        raise ValueError(f"GitHub user '{username}' not found.")
    response.raise_for_status()

    data = response.json()
    return {
        "username": data.get("login"),
        "name": data.get("name"),
        "bio": data.get("bio"),
        "public_repos": data.get("public_repos"),
        "followers": data.get("followers"),
        "profile_url": data.get("html_url")
    }


def fetch_github_repos(username: str, limit: int = 10) -> list:
    url = f"{GITHUB_API_BASE}/users/{username}/repos"
    params = {"sort": "updated", "per_page": limit}
    response = requests.get(url, params=params, timeout=10)

    if response.status_code == 404:
        raise ValueError(f"GitHub user '{username}' not found.")
    response.raise_for_status()

    repos = response.json()

    return [
        {
            "name": repo.get("name"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count"),
            "forks": repo.get("forks_count"),
            "url": repo.get("html_url"),
            "updated_at": repo.get("updated_at")
        }
        for repo in repos
    ]


def extract_languages_used(repos: list) -> list:
    languages = [repo["language"] for repo in repos if repo.get("language")]
    return sorted(set(languages))


def analyze_github_profile(username_or_url: str) -> dict:
    username = extract_username_from_input(username_or_url)
    profile = fetch_github_profile(username)
    repos = fetch_github_repos(username)
    languages = extract_languages_used(repos)

    return {
        "profile": profile,
        "repositories": repos,
        "languages_used": languages,
        "repo_count_analyzed": len(repos)
    }