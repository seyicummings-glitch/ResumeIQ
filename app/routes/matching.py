from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.resume_parser import extract_resume_text
from app.services.resume_structurer import structure_resume
from app.services.job_description_parser import parse_job_description
from app.services.matching_engine import calculate_overall_match
from app.services.keyword_analyzer import analyze_keywords
from app.services.github_analyzer import analyze_github_profile

router = APIRouter(prefix="/matching", tags=["Matching Engine"])


@router.post("/analyze")
async def analyze_match(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    github_username: str = Form(None)
):
    try:
        file_bytes = await file.read()
        resume_text = extract_resume_text(file.filename, file_bytes)
        resume_structured = structure_resume(resume_text)

        jd_parsed = parse_job_description(job_description)
        keyword_result = analyze_keywords(resume_text, jd_parsed["keywords"])

        github_languages = None
        github_note = None
        if github_username:
            try:
                github_profile = analyze_github_profile(github_username)
                github_languages = github_profile["languages_used"]
            except Exception as e:
                github_note = f"Could not incorporate GitHub data: {str(e)}"

        result = calculate_overall_match(
            resume_text=resume_text,
            resume_skills=resume_structured["skills"],
            jd_required_skills=jd_parsed["required_skills"],
            jd_experience_level=jd_parsed["experience_level"],
            jd_qualifications=jd_parsed["qualifications"],
            github_languages=github_languages
        )

        response = {
            "filename": file.filename,
            "resume_skills_found": resume_structured["skills"],
            "job_description_analysis": jd_parsed,
            "keyword_analysis": keyword_result,
            "match_result": result
        }
        if github_note:
            response["github_note"] = github_note

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing match: {str(e)}")
