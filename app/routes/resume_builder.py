from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.resume_builder import generate_enhanced_resume, chat_about_resume
from app.services.resume_structurer import extract_skills_list
from app.services.analysis_store import get_latest_analysis
from app.services.platform_settings import is_ai_enabled
from app.database import get_db
from app.models.models import Resume, User
from app.security import get_current_user

router = APIRouter(prefix="/resume-builder", tags=["AI Resume Builder"])


def _get_latest_active_resume(db: Session, user_id: int) -> Resume | None:
    return (
        db.query(Resume)
        .filter(Resume.user_id == user_id, Resume.is_active == True)  # noqa: E712
        .order_by(Resume.uploaded_at.desc())
        .first()
    )


@router.post("/generate")
def generate_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resume = _get_latest_active_resume(db, current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="No saved resume found. Upload and save a resume first.")

    analysis = get_latest_analysis(db, current_user.id, resume_id=resume.id)
    missing_skills = []
    if analysis and analysis.result_json:
        missing_skills = analysis.result_json.get("skill_match", {}).get("missing_skills", []) or []

    fallback_data = {
        "original_summary": resume.raw_text[:500] if resume.raw_text else "",
        "original_experience": resume.experience or "",
        "original_skills": extract_skills_list(resume.skills or ""),
    }

    result = generate_enhanced_resume(
        resume.raw_text or "",
        missing_skills,
        fallback_data,
        ai_enabled=is_ai_enabled(db),
    )
    result["resume_id"] = resume.id
    return result


class ResumeBuilderChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ResumeBuilderChatInput(BaseModel):
    conversation: list[ResumeBuilderChatMessage] = []
    current_summary: str = ""
    current_experience_bullets: list[str] = []
    current_skills_section: str = ""
    # Full text of a target job description (e.g. extracted from a URL the user
    # pasted in chat) — the AI itself can't browse links, so the frontend
    # extracts the real text via the existing /job-description/parse-url
    # pipeline and sends it here to ground the resume tailoring.
    jd_content: str = ""


@router.post("/chat")
def chat_resume(
    data: ResumeBuilderChatInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """One turn of conversational resume building/editing. The frontend keeps the running
    transcript and current draft client-side and resends both in full each turn — no
    server-side session state to manage. Always grounds on the user's current active resume
    if one exists (uploading a new file mid-conversation makes it the active resume, so the
    very next turn picks it up automatically); if none exists yet, the AI builds from whatever
    the user tells it in chat instead."""
    resume = _get_latest_active_resume(db, current_user.id)
    resume_text = ""
    missing_skills = []
    if resume:
        resume_text = resume.raw_text or ""
        analysis = get_latest_analysis(db, current_user.id, resume_id=resume.id)
        if analysis and analysis.result_json:
            missing_skills = analysis.result_json.get("skill_match", {}).get("missing_skills", []) or []

    conversation = [m.model_dump() for m in data.conversation]

    return chat_about_resume(
        conversation=conversation,
        resume_text=resume_text,
        missing_skills=missing_skills,
        current_summary=data.current_summary,
        current_experience_bullets=data.current_experience_bullets,
        current_skills_section=data.current_skills_section,
        ai_enabled=is_ai_enabled(db),
        jd_content=data.jd_content or None,
    )


class SaveEnhancedResumeInput(BaseModel):
    resume_id: int | None = None
    summary: str
    experience_bullets: list[str]
    skills_section: str


@router.post("/save")
def save_enhanced_resume(
    data: SaveEnhancedResumeInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Saves the chat-built draft as a new resume version. resume_id is optional: if the draft
    was built entirely from scratch through conversation (no prior uploaded resume), there's no
    source row to version from, so this creates a fresh one instead of extending a lineage."""
    original = None
    if data.resume_id is not None:
        original = db.query(Resume).filter(
            Resume.id == data.resume_id, Resume.user_id == current_user.id
        ).first()
        if not original:
            raise HTTPException(status_code=404, detail="Source resume not found.")

    experience_text = "\n".join(data.experience_bullets)
    raw_text = (
        f"SUMMARY\n{data.summary}\n\n"
        f"EXPERIENCE\n{experience_text}\n\n"
        f"SKILLS\n{data.skills_section}"
    )
    new_skills = extract_skills_list(data.skills_section)

    # Version numbers must be unique per user, not just "original + 1" — two
    # saves off the same source resume would otherwise both claim v2.
    highest_version = (
        db.query(Resume.version)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.version.desc())
        .first()
    )
    new_version = (highest_version[0] if highest_version else 0) + 1

    new_resume = Resume(
        user_id=current_user.id,
        filename=f"{original.filename} (AI-enhanced)" if original else "AI-built resume",
        raw_text=raw_text,
        skills=", ".join(new_skills),
        experience=experience_text,
        education=original.education if original else None,
        certifications=original.certifications if original else None,
        projects=original.projects if original else None,
        version=new_version,
        label=f"v{new_version} (AI-enhanced)" if original else f"v{new_version} (AI-built)",
        is_active=True
    )

    # Exactly one resume can be "active" per user — deactivate every other
    # version, not just the one this save started from.
    db.query(Resume).filter(Resume.user_id == current_user.id).update({Resume.is_active: False})

    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    return {
        "message": "Enhanced resume saved as a new version.",
        "resume_id": new_resume.id,
        "version": new_resume.version,
        "label": new_resume.label
    }
