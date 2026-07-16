from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.resume_parser import extract_resume_text
from app.services.resume_structurer import structure_resume
from app.services.job_description_parser import parse_job_description
from app.services.matching_engine import calculate_overall_match

router = APIRouter(prefix="/matching", tags=["Matching Engine"])


@router.post("/analyze")
async def analyze_match(
    file: UploadFile = File(...),
    job_description: str = Form(...)
):
    try:
        file_bytes = await file.read()
        resume_text = extract_resume_text(file.filename, file_bytes)
        resume_structured = structure_resume(resume_text)

        jd_parsed = parse_job_description(job_description)

        result = calculate_overall_match(
            resume_text=resume_text,
            resume_skills=resume_structured["skills"],
            jd_required_skills=jd_parsed["required_skills"],
            jd_experience_level=jd_parsed["experience_level"],
            jd_qualifications=jd_parsed["qualifications"]
        )

        return {
            "filename": file.filename,
            "resume_skills_found": resume_structured["skills"],
            "job_description_analysis": jd_parsed,
            "match_result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing match: {str(e)}")