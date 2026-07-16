from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.github_analyzer import analyze_github_profile

router = APIRouter(prefix="/github", tags=["GitHub Analyzer"])


class GitHubInput(BaseModel):
    username_or_url: str


@router.post("/analyze")
def analyze_github(data: GitHubInput):
    try:
        result = analyze_github_profile(data.username_or_url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing GitHub profile: {str(e)}")