from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests
from bs4 import BeautifulSoup
from app.services.job_description_parser import parse_job_description, derive_job_title
from app.services.job_description_ai import parse_job_description_ai
from app.services.resume_parser import extract_resume_text
from app.services.platform_settings import is_ai_enabled
from app.database import get_db
from app.models.models import JobDescription, User
from app.schemas import JobDescriptionCreate, JobDescriptionResponse
from app.security import get_current_user

router = APIRouter(prefix="/job-description", tags=["Job Description"])

# CSS selectors known to hold just the posting body on common job boards —
# tried in order; the first one that actually matches with real content wins,
# which is far more precise than dumping the whole page's text.
_MAIN_CONTENT_SELECTORS = [
    ".description__text",  # LinkedIn
    ".show-more-less-html__markup",  # LinkedIn (expanded description)
    "#jobDescriptionText",  # Indeed
    "#content .opening",  # Greenhouse
    "#content",  # Greenhouse (generic)
    ".posting-page",  # Lever
    ".section-wrapper",  # Lever
    "[data-testid='jobDescriptionText']",
    "article",
    "main",
    "[role='main']",
]

# Short, common UI strings that survive tag-stripping on job boards but are
# never part of the actual posting — removed as a last cleanup pass.
_BOILERPLATE_PHRASES = [
    "Skip to main content",
    "Apply Save Report this job",
    "Apply now",
    "Save job",
    "Report this job",
    "Sign in to see who",
    "See who",
    "has hired for this role",
    "Direct message the job poster",
    "We use cookies",
    "Accept cookies",
    "Accept all cookies",
]

_NOISE_CLASS_KEYWORDS = [
    "cookie", "banner", "menu", "sidebar", "social", "share", "subscribe",
    "newsletter", "advert", "promo", "related", "similar", "breadcrumb",
    "pagination", "comment",
]


def _extract_job_posting_text(soup: BeautifulSoup) -> str:
    """Best-effort extraction of just the job posting body from a scraped
    page, without a full headless browser or main-content-extraction library:
    strip obvious chrome, prefer a known job-board content container when one
    matches, and fall back to the whole page's text only as a last resort."""
    for tag in soup(["script", "style", "nav", "header", "footer", "svg", "noscript", "iframe", "form", "button", "aside"]):
        tag.decompose()

    for element in soup.find_all(class_=True) + soup.find_all(id=True):
        # Decomposing a parent earlier in this list detaches any of its
        # children that also appear later in it — skip those rather than
        # touching a dead Tag.
        if getattr(element, "decomposed", False):
            continue
        identifiers = " ".join(element.get("class") or []) + " " + (element.get("id") or "")
        if any(keyword in identifiers.lower() for keyword in _NOISE_CLASS_KEYWORDS):
            element.decompose()

    for selector in _MAIN_CONTENT_SELECTORS:
        match = soup.select_one(selector)
        if match:
            candidate = match.get_text(separator=" ", strip=True)
            if len(candidate) > 150:
                return candidate

    text = soup.get_text(separator=" ", strip=True)
    for phrase in _BOILERPLATE_PHRASES:
        text = text.replace(phrase, " ")
    return " ".join(text.split())


def _parse_with_ai_fallback(text: str, db: Session) -> dict:
    """AI-first job description parsing: real, named skills instead of raw
    word-frequency noise. Falls back to the rule-based parser (and echoes the
    original text back as "cleaned_description") when AI is unavailable."""
    ai_result = parse_job_description_ai(text, ai_enabled=is_ai_enabled(db))
    if ai_result:
        return {**ai_result, "source": "ai"}

    fallback = parse_job_description(text)
    return {**fallback, "title": "", "cleaned_description": text, "source": "fallback"}


class JobDescriptionInput(BaseModel):
    content: str


@router.post("/parse")
def parse_jd_text(data: JobDescriptionInput, db: Session = Depends(get_db)):
    result = _parse_with_ai_fallback(data.content, db)
    return {"source": result["source"], "job_description_analysis": result}


@router.post("/parse-file")
async def parse_jd_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_bytes = await file.read()
        text = extract_resume_text(file.filename, file_bytes)
        result = _parse_with_ai_fallback(text, db)
        return {
            "source": result["source"],
            "filename": file.filename,
            "extracted_text_preview": result["cleaned_description"],
            "job_description_analysis": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


class JobDescriptionURLInput(BaseModel):
    url: str


@router.post("/parse-url")
def parse_jd_url(data: JobDescriptionURLInput, db: Session = Depends(get_db)):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(data.url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        text = _extract_job_posting_text(soup)

        if len(text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract meaningful content from this URL.")

        result = _parse_with_ai_fallback(text, db)
        return {
            "source": result["source"],
            "url": data.url,
            "extracted_text_preview": result["cleaned_description"],
            "job_description_analysis": result
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing URL: {str(e)}")


def _auto_extract_title(content: str, db: Session) -> str | None:
    """Best-effort title extraction when the client didn't send one — tries the AI parser
    first (real title, e.g. "Backend Developer"), then the safe first-line heuristic. Returns
    None (not the display placeholder) when nothing usable was found, so the caller can tell
    the difference between "we have a title" and "we don't"."""
    ai_result = parse_job_description_ai(content, ai_enabled=is_ai_enabled(db))
    if ai_result and ai_result.get("title"):
        return ai_result["title"]
    heuristic_title = derive_job_title(None, content)
    return heuristic_title if heuristic_title != "Untitled job description" else None


@router.post("/save", response_model=JobDescriptionResponse)
def save_job_description(
    data: JobDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # The frontend resolves a title before calling this (AI-extracted or typed by the user) —
    # this is a safety net for any caller that didn't, so a JobDescription is never saved
    # with an avoidably-missing title.
    title = data.title or _auto_extract_title(data.content, db)

    new_jd = JobDescription(
        user_id=current_user.id,
        title=title,
        content=data.content
    )
    db.add(new_jd)
    db.commit()
    db.refresh(new_jd)
    return new_jd


@router.get("/my-job-descriptions", response_model=list[JobDescriptionResponse])
def get_my_job_descriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(JobDescription).filter(JobDescription.user_id == current_user.id).all()