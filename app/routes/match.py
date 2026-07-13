from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.resume_parser import extract_resume_text
from app.services.match_scorer import calculate_match_score

router = APIRouter(prefix="/match", tags=["Match Scoring"])


@router.post("/score")
async def score_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...)
):
    try:
        file_bytes = await file.read()
        resume_text = extract_resume_text(file.filename, file_bytes)
        result = calculate_match_score(resume_text, job_description)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scoring resume: {str(e)}")