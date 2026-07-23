from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.resume_parser import extract_resume_text
from app.services.resume_structurer import structure_resume
from app.services.ats_scorer import calculate_ats_score
from app.database import get_db
from app.models.models import Resume, User
from app.security import get_current_user

router = APIRouter(prefix="/resume", tags=["Resume"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_file(file: UploadFile, file_bytes: bytes):
    filename = file.filename.lower()
    file_extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_extension}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
        )


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes)

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
async def structure_resume_endpoint(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes)

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
async def ats_score_resume(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes)

        text = extract_resume_text(file.filename, file_bytes)
        structured_data = structure_resume(text)
        ats_result = calculate_ats_score(file.filename, text, structured_data)

        return {
            "filename": file.filename,
            "ats_result": ats_result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scoring resume: {str(e)}")


@router.post("/save")
async def save_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes)

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
            projects=structured_data.get("projects", "")
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