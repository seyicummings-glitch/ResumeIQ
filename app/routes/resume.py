from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.services.resume_parser import extract_resume_text
from app.services.resume_structurer import structure_resume, extract_skills_list
from app.services.ats_scorer import calculate_ats_score
from app.services.ai_suggestions import generate_resume_suggestions
from app.services.job_description_parser import parse_job_description, derive_job_title
from app.services.keyword_analyzer import analyze_keywords
from app.services.platform_settings import get_upload_limits, is_ai_enabled
from app.database import get_db
from app.models.models import Resume, User, AnalysisResult, JobDescription
from app.security import get_current_user

router = APIRouter(prefix="/resume", tags=["Resume"])


def validate_file(file: UploadFile, file_bytes: bytes, db: Session):
    """Enforces the admin-configured max upload size / allowed file types
    (Admin Settings page) instead of fixed constants."""
    allowed_extensions, max_size_mb = get_upload_limits(db)
    max_size_bytes = max_size_mb * 1024 * 1024

    filename = file.filename.lower()
    file_extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_extension}'. Allowed types: {', '.join(sorted(allowed_extensions))}"
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is {max_size_mb}MB."
        )


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes, db)

        text = extract_resume_text(file.filename, file_bytes)
        return {
            "filename": file.filename,
            "extracted_text_preview": text[:500],
            "character_count": len(text)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/structure")
async def structure_resume_endpoint(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes, db)

        text = extract_resume_text(file.filename, file_bytes)
        structured_data = structure_resume(text)
        return {
            "filename": file.filename,
            "structured_data": structured_data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error structuring resume: {str(e)}")


@router.post("/ats-score")
async def ats_score_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes, db)

        text = extract_resume_text(file.filename, file_bytes)
        structured_data = structure_resume(text)
        ats_result = calculate_ats_score(file.filename, text, structured_data)

        return {
            "filename": file.filename,
            "ats_result": ats_result,
            "contact_info": structured_data["contact_info"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scoring resume: {str(e)}")


@router.post("/ai-suggestions")
async def ai_suggestions_resume(
    file: UploadFile = File(...),
    job_description: str = Form(None),
    db: Session = Depends(get_db),
):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes, db)

        text = extract_resume_text(file.filename, file_bytes)
        structured_data = structure_resume(text)
        ats_result = calculate_ats_score(file.filename, text, structured_data)

        fallback_data = {"ats_issues": ats_result["issues"]}
        if job_description:
            jd_parsed = parse_job_description(job_description)
            keyword_result = analyze_keywords(text, jd_parsed["keywords"])
            fallback_data["missing_keywords"] = keyword_result["missing_keywords"]

        result = generate_resume_suggestions(text, job_description, fallback_data, ai_enabled=is_ai_enabled(db))

        return {
            "filename": file.filename,
            "ai_suggestions": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")


@router.post("/save")
async def save_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes, db)

        text = extract_resume_text(file.filename, file_bytes)
        structured_data = structure_resume(text)

        new_resume = Resume(
            user_id=current_user.id,
            filename=file.filename,
            raw_text=text,
            skills=", ".join(structured_data.get("skills", [])),
            experience=structured_data.get("experience", ""),
            education=structured_data.get("education", ""),
            certifications=structured_data.get("certifications", ""),
            projects=structured_data.get("projects", ""),
            file_data=file_bytes,
            file_content_type=file.content_type,
        )
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)

        return {
            "message": "Resume saved successfully.",
            "resume_id": new_resume.id,
            "filename": new_resume.filename,
            "uploaded_at": new_resume.uploaded_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving resume: {str(e)}")


@router.get("/my-resumes")
def get_my_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    return resumes


def _latest_analysis_for_resume(db: Session, resume_id: int) -> AnalysisResult | None:
    return (
        db.query(AnalysisResult)
        .filter(AnalysisResult.resume_id == resume_id)
        .order_by(AnalysisResult.created_at.desc())
        .first()
    )


def _resume_version_summary(db: Session, resume: Resume) -> dict:
    analysis = _latest_analysis_for_resume(db, resume.id)
    latest_scores = None
    if analysis and analysis.result_json:
        latest_scores = {
            "overall_match_score": analysis.result_json.get("overall_match_score"),
            "skill_match": analysis.result_json.get("skill_match"),
        }

    latest_job_title = None
    if analysis:
        job = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()
        if job:
            latest_job_title = derive_job_title(job.title, job.content)

    return {
        "id": resume.id,
        "filename": resume.filename,
        "label": resume.label,
        "version": resume.version,
        "is_active": resume.is_active,
        "uploaded_at": resume.uploaded_at,
        "skills": extract_skills_list(resume.skills or ""),
        "experience": resume.experience,
        "education": resume.education,
        "certifications": resume.certifications,
        "projects": resume.projects,
        "latest_scores": latest_scores,
        # Lets the frontend wire "Re-analyze" straight into POST /matching/save and
        # "View" into the existing analysis results page, without a second round-trip.
        "latest_analysis_id": analysis.id if analysis else None,
        "latest_job_description_id": analysis.job_description_id if analysis else None,
        "latest_job_title": latest_job_title,
        "has_downloadable_file": resume.file_data is not None,
    }


@router.get("/versions")
def get_resume_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.version.desc())
        .all()
    )
    return [_resume_version_summary(db, resume) for resume in resumes]


@router.get("/versions/compare")
def compare_resume_versions(
    a: int,
    b: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resume_a = db.query(Resume).filter(Resume.id == a, Resume.user_id == current_user.id).first()
    if not resume_a:
        raise HTTPException(status_code=404, detail=f"Resume {a} not found.")

    resume_b = db.query(Resume).filter(Resume.id == b, Resume.user_id == current_user.id).first()
    if not resume_b:
        raise HTTPException(status_code=404, detail=f"Resume {b} not found.")

    analysis_a = _latest_analysis_for_resume(db, resume_a.id)
    analysis_b = _latest_analysis_for_resume(db, resume_b.id)

    skill_diff = None
    if analysis_a and analysis_a.result_json and analysis_b and analysis_b.result_json:
        missing_a = {
            s.lower() for s in analysis_a.result_json.get("skill_match", {}).get("missing_skills", []) or []
        }
        missing_b = {
            s.lower() for s in analysis_b.result_json.get("skill_match", {}).get("missing_skills", []) or []
        }
        resolved = sorted(missing_b - missing_a)
        remaining = sorted(missing_a & missing_b)
        added = sorted(missing_a - missing_b)
        skill_diff = {"resolved": resolved, "remaining": remaining, "added": added}

    return {
        "resume_a": _resume_version_summary(db, resume_a),
        "resume_b": _resume_version_summary(db, resume_b),
        "skill_diff": skill_diff,
    }


@router.get("/{resume_id}/download")
def download_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    if resume.file_data is not None:
        return Response(
            content=resume.file_data,
            media_type=resume.file_content_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{resume.filename}"'},
        )

    # Resumes saved before file storage was added have no original bytes on
    # file — fall back to the parsed text so the download still works.
    fallback_name = resume.filename.rsplit(".", 1)[0] + ".txt"
    return Response(
        content=resume.raw_text or "",
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{fallback_name}"'},
    )


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    # AnalysisResult.resume_id has no ON DELETE CASCADE, so dependent analyses
    # are removed explicitly first or the delete would violate the FK constraint.
    db.query(AnalysisResult).filter(AnalysisResult.resume_id == resume_id).delete()
    db.delete(resume)
    db.commit()

    return {"message": "Resume deleted."}