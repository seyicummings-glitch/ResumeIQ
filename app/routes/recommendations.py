from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Resume, JobDescription, User
from app.security import get_current_user
from app.services.resume_structurer import extract_skills_list
from app.services.recommendation_engine import rank_jobs_for_resume

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/jobs")
def get_job_recommendations(
    resume_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if resume_id is not None:
        resume = db.query(Resume).filter(
            Resume.id == resume_id, Resume.user_id == current_user.id
        ).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found.")
    else:
        resume = (
            db.query(Resume)
            .filter(Resume.user_id == current_user.id)
            .order_by(Resume.uploaded_at.desc())
            .first()
        )
        if not resume:
            raise HTTPException(
                status_code=404,
                detail="No saved resumes found. Save one via /resume/save first."
            )

    job_descriptions = db.query(JobDescription).filter(
        JobDescription.user_id == current_user.id
    ).all()

    if not job_descriptions:
        return {
            "resume_id": resume.id,
            "filename": resume.filename,
            "recommendations": [],
            "message": "No saved job descriptions. Save one via /job-description/save first."
        }

    resume_skills = extract_skills_list(resume.skills or "")
    jd_payload = [
        {"id": jd.id, "title": jd.title, "content": jd.content}
        for jd in job_descriptions
    ]
    ranked = rank_jobs_for_resume(resume.raw_text or "", resume_skills, jd_payload)

    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "recommendations": ranked
    }
