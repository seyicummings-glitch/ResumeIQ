from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.resume_parser import extract_resume_text
from app.services.resume_structurer import structure_resume
from app.services.job_description_parser import parse_job_description, derive_job_title
from app.services.job_description_ai import parse_job_description_ai
from app.services.matching_engine import calculate_overall_match
from app.services.keyword_analyzer import analyze_keywords
from app.services.ats_scorer import calculate_ats_score
from app.services.github_analyzer import analyze_github_profile
from app.services.writing_scorer import calculate_writing_score
from app.services.readiness_scorer import calculate_hiring_readiness, explain_hiring_readiness
from app.services.ai_suggestions import generate_resume_suggestions
from app.services.platform_settings import is_ai_enabled
from app.database import get_db
from app.models.models import Resume, JobDescription, AnalysisResult, User
from app.models.document_models import GeneratedDocument
from app.security import get_current_user

router = APIRouter(prefix="/matching", tags=["Matching Engine"])


def _parse_jd_accurately(text: str, db: Session) -> dict:
    """AI-first job description parsing (real, named skills) with a
    rule-based fallback — see app/services/job_description_ai.py."""
    ai_result = parse_job_description_ai(text, ai_enabled=is_ai_enabled(db))
    if ai_result:
        return ai_result
    return parse_job_description(text)


@router.post("/analyze")
async def analyze_match(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    github_username: str = Form(None),
    db: Session = Depends(get_db),
):
    try:
        file_bytes = await file.read()
        resume_text = extract_resume_text(file.filename, file_bytes)
        resume_structured = structure_resume(resume_text)

        jd_parsed = _parse_jd_accurately(job_description, db)
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


class AnalysisSaveInput(BaseModel):
    resume_id: int
    job_description_id: int


@router.post("/save")
def save_analysis(
    data: AnalysisSaveInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Recompute a resume-vs-JD match and persist it as an AnalysisResult, so
    downstream features (skill assessment, interview practice, learning
    roadmap, version history, admin analytics) have a real "latest analysis"
    to read from instead of the stateless /matching/analyze response."""
    try:
        resume = db.query(Resume).filter(
            Resume.id == data.resume_id, Resume.user_id == current_user.id
        ).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found.")

        job_description = db.query(JobDescription).filter(
            JobDescription.id == data.job_description_id, JobDescription.user_id == current_user.id
        ).first()
        if not job_description:
            raise HTTPException(status_code=404, detail="Job description not found.")

        # Re-derive skills fresh from the resume's raw text on every analysis, rather
        # than trusting the `resume.skills` string stored at upload time — that stored
        # value is whatever the skill-extraction logic produced back when the resume
        # was first uploaded, so it goes stale (and never benefits from extraction
        # improvements) unless the resume is re-uploaded. Freshly parsing here also
        # lets one structure_resume() call feed both the skill match and the ATS/
        # writing scorers below, so they always agree on what skills were found.
        structured_data = structure_resume(resume.raw_text or "")
        resume_skills = structured_data["skills"]
        jd_parsed = _parse_jd_accurately(job_description.content, db)

        # The user didn't type a title when pasting this JD — the AI parse above already
        # extracted the real one (job_description_ai.JD_SCHEMA's "title" field), so persist
        # it now rather than guessing from the raw text every time it's displayed.
        if not job_description.title and jd_parsed.get("title"):
            job_description.title = jd_parsed["title"]

        result = calculate_overall_match(
            resume_text=resume.raw_text or "",
            resume_skills=resume_skills,
            jd_required_skills=jd_parsed["required_skills"],
            jd_experience_level=jd_parsed["experience_level"],
            jd_qualifications=jd_parsed["qualifications"]
        )

        ats_result = calculate_ats_score(resume.filename, resume.raw_text or "", structured_data)
        keyword_analysis = analyze_keywords(resume.raw_text or "", jd_parsed["keywords"])
        writing_result = calculate_writing_score(structured_data)
        hiring_readiness_score = calculate_hiring_readiness(
            ats_score=ats_result["overall_ats_score"],
            match_score=result["overall_match_score"],
            skill_score=result["skill_match"]["skill_score"],
            writing_score=writing_result["overall_writing_score"],
        )
        hiring_readiness_explanation = explain_hiring_readiness(
            hiring_readiness_score,
            ats_score=ats_result["overall_ats_score"],
            match_score=result["overall_match_score"],
            skill_score=result["skill_match"]["skill_score"],
            writing_score=writing_result["overall_writing_score"],
        )

        result["ats_result"] = ats_result
        result["keyword_analysis"] = keyword_analysis
        result["writing_result"] = writing_result
        result["hiring_readiness_score"] = hiring_readiness_score
        result["hiring_readiness_explanation"] = hiring_readiness_explanation

        analysis = AnalysisResult(
            user_id=current_user.id,
            resume_id=resume.id,
            job_description_id=job_description.id,
            match_percentage=round(result["overall_match_score"]),
            result_json=result
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return {
            "message": "Analysis saved.",
            "analysis_id": analysis.id,
            "resume_id": resume.id,
            "job_description_id": job_description.id,
            "match_result": result,
            "created_at": analysis.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving analysis: {str(e)}")


@router.get("/history")
def get_analysis_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(AnalysisResult, Resume, JobDescription)
        .join(Resume, Resume.id == AnalysisResult.resume_id)
        .join(JobDescription, JobDescription.id == AnalysisResult.job_description_id)
        .filter(AnalysisResult.user_id == current_user.id)
        .order_by(AnalysisResult.created_at.desc())
        .all()
    )
    return [
        {
            "id": analysis.id,
            "resume_id": analysis.resume_id,
            "resume_filename": resume.filename,
            "job_description_id": analysis.job_description_id,
            "job_description_title": derive_job_title(job_description.title, job_description.content),
            "match_percentage": analysis.match_percentage,
            "match_result": analysis.result_json,
            "created_at": analysis.created_at
        }
        for analysis, resume, job_description in rows
    ]


def _analysis_summary(db: Session, analysis: AnalysisResult) -> dict:
    resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
    job_description = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()
    result_json = analysis.result_json or {}

    return {
        "id": analysis.id,
        "resume_filename": resume.filename if resume else None,
        "job_description_title": derive_job_title(job_description.title, job_description.content) if job_description else None,
        "overall_match_score": result_json.get("overall_match_score"),
        "skill_match": result_json.get("skill_match"),
        "created_at": analysis.created_at,
    }


@router.get("/compare")
def compare_analyses(
    a: int,
    b: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Registered before /{analysis_id} — Starlette matches routes in
    # declaration order, and {analysis_id} would otherwise greedily swallow
    # a literal "/matching/compare" request and 422 on the int conversion.
    analysis_a = db.query(AnalysisResult).filter(AnalysisResult.id == a, AnalysisResult.user_id == current_user.id).first()
    if not analysis_a:
        raise HTTPException(status_code=404, detail=f"Analysis {a} not found.")

    analysis_b = db.query(AnalysisResult).filter(AnalysisResult.id == b, AnalysisResult.user_id == current_user.id).first()
    if not analysis_b:
        raise HTTPException(status_code=404, detail=f"Analysis {b} not found.")

    missing_a = {s.lower() for s in (analysis_a.result_json or {}).get("skill_match", {}).get("missing_skills", []) or []}
    missing_b = {s.lower() for s in (analysis_b.result_json or {}).get("skill_match", {}).get("missing_skills", []) or []}
    skill_diff = {
        "resolved": sorted(missing_a - missing_b),
        "remaining": sorted(missing_a & missing_b),
        "added": sorted(missing_b - missing_a),
    }

    return {
        "analysis_a": _analysis_summary(db, analysis_a),
        "analysis_b": _analysis_summary(db, analysis_b),
        "skill_diff": skill_diff,
    }


@router.get("/{analysis_id}")
def get_analysis_detail(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analysis = db.query(AnalysisResult).filter(
        AnalysisResult.id == analysis_id, AnalysisResult.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
    job_description = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()

    return {
        "id": analysis.id,
        "resume_id": analysis.resume_id,
        "resume_filename": resume.filename if resume else None,
        "job_description_id": analysis.job_description_id,
        "job_description_title": derive_job_title(job_description.title, job_description.content) if job_description else None,
        "match_percentage": analysis.match_percentage,
        "match_result": analysis.result_json,
        "created_at": analysis.created_at
    }


@router.post("/{analysis_id}/suggestions")
def get_analysis_suggestions(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """AI-powered suggestions for an already-saved analysis, using the resume's stored
    parsed text — unlike /resume/ai-suggestions, no file re-upload is needed."""
    analysis = db.query(AnalysisResult).filter(
        AnalysisResult.id == analysis_id, AnalysisResult.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
    job_description = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()
    if not resume or not job_description:
        raise HTTPException(status_code=404, detail="Source resume or job description no longer available.")

    result_json = analysis.result_json or {}
    fallback_data = {
        "ats_issues": result_json.get("ats_result", {}).get("issues", []),
        "missing_keywords": result_json.get("keyword_analysis", {}).get("missing_keywords", []),
    }

    ai_suggestions = generate_resume_suggestions(
        resume.raw_text or "",
        job_description.content,
        fallback_data,
        ai_enabled=is_ai_enabled(db)
    )

    return {"ai_suggestions": ai_suggestions}


@router.delete("/{analysis_id}")
def delete_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analysis = db.query(AnalysisResult).filter(
        AnalysisResult.id == analysis_id, AnalysisResult.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    # Generated PDF reports reference the analysis but stay valid on their own,
    # so detach rather than delete them.
    db.query(GeneratedDocument).filter(GeneratedDocument.analysis_id == analysis_id).update({"analysis_id": None})
    db.delete(analysis)
    db.commit()

    return {"message": "Analysis deleted."}
