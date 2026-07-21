from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests
from bs4 import BeautifulSoup
from app.services.job_description_parser import parse_job_description
from app.services.resume_parser import extract_resume_text
from app.database import get_db
from app.models.models import JobDescription, User
from app.schemas import JobDescriptionCreate, JobDescriptionResponse
from app.security import get_current_user

router = APIRouter(prefix="/job-description", tags=["Job Description"])


class JobDescriptionInput(BaseModel):
    content: str


@router.post("/parse")
def parse_jd_text(data: JobDescriptionInput):
    result = parse_job_description(data.content)
    return {"source": "text", "job_description_analysis": result}


@router.post("/parse-file")
async def parse_jd_file(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        text = extract_resume_text(file.filename, file_bytes)
        result = parse_job_description(text)
        return {
            "source": "file",
            "filename": file.filename,
            "extracted_text_preview": text[:500],
            "job_description_analysis": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


class JobDescriptionURLInput(BaseModel):
    url: str


@router.post("/parse-url")
def parse_jd_url(data: JobDescriptionURLInput):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(data.url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        if len(text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract meaningful content from this URL.")

        result = parse_job_description(text)
        return {
            "source": "url",
            "url": data.url,
            "extracted_text_preview": text[:500],
            "job_description_analysis": result
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing URL: {str(e)}")


@router.post("/save", response_model=JobDescriptionResponse)
def save_job_description(
    data: JobDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_jd = JobDescription(
        user_id=current_user.id,
        title=data.title,
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