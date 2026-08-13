import base64
import binascii
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.resume_builder import generate_enhanced_resume, chat_about_resume
from app.services.resume_structurer import extract_skills_list
from app.services.analysis_store import get_latest_analysis
from app.services.platform_settings import is_ai_enabled
from app.services.attachment_ai import analyze_attachment
from app.services.analytics import track_event, EVENT_TYPES, FEATURE_AI_BUILDER
from app.services.feature_gate import check_and_consume, FeatureAccessDenied
from app.security import get_session_id_from_request
from app.database import get_db
from app.models.models import Resume, User
from app.security import get_current_user

router = APIRouter(prefix="/resume-builder", tags=["AI Resume Builder"])

# Attachments are sent base64-encoded inside the JSON chat request rather than as a separate
# multipart upload, to keep this one request/response shape like the rest of this API — fine
# for the images/screenshots/PDFs/short documents this feature targets, not meant for large
# files. 8MB decoded (~10.9MB base64-encoded) matches the resume upload limit's default.
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024


def _get_latest_active_resume(db: Session, user_id: int) -> Resume | None:
    return (
        db.query(Resume)
        .filter(Resume.user_id == user_id, Resume.is_active == True)  # noqa: E712
        .order_by(Resume.uploaded_at.desc())
        .first()
    )


def _contact_info(user: User) -> dict:
    """Real contact details, straight from the user's own profile — never
    AI-generated. Keeping this entirely separate from the AI-produced draft
    means the model is never even in a position to invent a name, email,
    phone number, location, or portfolio link."""
    return {
        "full_name": user.full_name or "",
        "email": user.email or "",
        "phone": user.phone or "",
        "linkedin": user.linkedin_url or "",
        "location": user.location or "",
        "portfolio": user.portfolio_url or "",
    }


@router.post("/generate")
def generate_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    resume = _get_latest_active_resume(db, current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="No saved resume found. Upload and save a resume first.")

    try:
        check_and_consume(db, current_user, "ai_resume_builder")
    except FeatureAccessDenied as exc:
        raise HTTPException(status_code=402, detail=exc.payload)

    analysis = get_latest_analysis(db, current_user.id, resume_id=resume.id)
    missing_skills = []
    if analysis and analysis.result_json:
        missing_skills = analysis.result_json.get("skill_match", {}).get("missing_skills", []) or []

    fallback_data = {
        "original_summary": resume.raw_text[:500] if resume.raw_text else "",
        "original_experience": resume.experience or "",
        "original_education": resume.education or "",
        "original_certifications": resume.certifications or "",
        "original_projects": resume.projects or "",
        "original_skills": extract_skills_list(resume.skills or ""),
        "original_title": current_user.target_role or "",
        # Used only to keep generated content coherent with the candidate's actual field (e.g.
        # never surfacing software-engineering skills on a marketing resume) — never as license
        # to invent experience; see _role_context_block in the service layer.
        "target_role": current_user.target_role or "",
        "target_industry": current_user.industry or "",
    }

    result = generate_enhanced_resume(
        resume.raw_text or "",
        missing_skills,
        fallback_data,
        ai_enabled=is_ai_enabled(db),
    )
    result["resume_id"] = resume.id
    result["contact"] = _contact_info(current_user)

    track_event(
        db, EVENT_TYPES["AI_RESUME_SUGGESTION_GENERATED"], FEATURE_AI_BUILDER, user_id=current_user.id,
        metadata={"resume_id": resume.id}, request=request, session_id=get_session_id_from_request(request),
    )
    return result


class ResumeBuilderChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatAttachment(BaseModel):
    filename: str
    mime_type: str
    data_base64: str


class ExperienceItemInput(BaseModel):
    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = []


class EducationItemInput(BaseModel):
    degree: str = ""
    school: str = ""
    date: str = ""


class SkillsInput(BaseModel):
    technical: list[str] = []
    soft: list[str] = []


class ProjectItemInput(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = []
    bullets: list[str] = []  # results achieved


class LanguageItemInput(BaseModel):
    name: str = ""
    proficiency: str = ""


class ResumeBuilderChatInput(BaseModel):
    conversation: list[ResumeBuilderChatMessage] = []
    current_title: str = ""
    current_summary: str = ""
    current_skills: SkillsInput = SkillsInput()
    current_experience: list[ExperienceItemInput] = []
    current_education: list[EducationItemInput] = []
    current_certifications: list[str] = []
    current_projects: list[ProjectItemInput] = []
    current_languages: list[LanguageItemInput] = []
    current_references: list[str] = []
    # Full text of a target job description (e.g. extracted from a URL the user
    # pasted in chat) — the AI itself can't browse links, so the frontend
    # extracts the real text via the existing /job-description/parse-url
    # pipeline and sends it here to ground the resume tailoring.
    jd_content: str = ""
    # An image, screenshot, PDF, or document attached to this turn's message, if any.
    attachment: ChatAttachment | None = None

    def draft_dict(self) -> dict:
        return {
            "title": self.current_title,
            "summary": self.current_summary,
            "skills": self.current_skills.model_dump(),
            "experience": [item.model_dump() for item in self.current_experience],
            "education": [item.model_dump() for item in self.current_education],
            "certifications": self.current_certifications,
            "projects": [item.model_dump() for item in self.current_projects],
            "languages": [item.model_dump() for item in self.current_languages],
            "references": self.current_references,
        }


@router.post("/chat")
def chat_resume(
    data: ResumeBuilderChatInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """One turn of conversational resume building/editing. The frontend keeps the running
    transcript and current draft client-side and resends both in full each turn — no
    server-side session state to manage. Always grounds on the user's current active resume
    if one exists (uploading a new file mid-conversation makes it the active resume, so the
    very next turn picks it up automatically); if none exists yet, the AI builds from whatever
    the user tells it in chat instead.

    If an attachment came with this turn, it's analyzed once here (see attachment_ai.py — real
    vision for images/PDFs, extracted text for other documents) and folded into the last user
    message as extra context, rather than resent as binary on every future turn."""
    if not data.conversation:
        # An empty conversation is the de facto "start" of a builder session — there's no
        # explicit start/end handshake in this stateless, resend-the-transcript design.
        track_event(
            db, EVENT_TYPES["AI_BUILDER_STARTED"], FEATURE_AI_BUILDER, user_id=current_user.id,
            request=request, session_id=get_session_id_from_request(request),
        )

    resume = _get_latest_active_resume(db, current_user.id)
    resume_text = ""
    missing_skills = []
    if resume:
        resume_text = resume.raw_text or ""
        analysis = get_latest_analysis(db, current_user.id, resume_id=resume.id)
        if analysis and analysis.result_json:
            missing_skills = analysis.result_json.get("skill_match", {}).get("missing_skills", []) or []

    conversation = [m.model_dump() for m in data.conversation]
    draft = data.draft_dict()

    if data.attachment:
        try:
            file_bytes = base64.b64decode(data.attachment.data_base64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail="Attachment data is not valid base64.")
        if len(file_bytes) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=400, detail="Attachment is too large (max 8MB).")

        last_user_message = conversation[-1]["content"] if conversation else ""
        analysis_result = analyze_attachment(
            file_bytes=file_bytes,
            mime_type=data.attachment.mime_type,
            filename=data.attachment.filename,
            user_message=last_user_message or None,
            ai_enabled=is_ai_enabled(db),
        )

        if analysis_result["description"] is None:
            return {
                "reply": analysis_result["message"] or "Couldn't analyze that attachment. Your draft wasn't changed.",
                **draft,
                "source": "fallback",
                "contact": _contact_info(current_user),
            }

        attachment_note = f"\n\n[Attached file: {data.attachment.filename}]\n{analysis_result['description']}"
        if conversation:
            conversation[-1]["content"] = (conversation[-1]["content"] or "") + attachment_note
        else:
            conversation.append({"role": "user", "content": attachment_note.strip()})

    result = chat_about_resume(
        conversation=conversation,
        resume_text=resume_text,
        missing_skills=missing_skills,
        current_draft=draft,
        ai_enabled=is_ai_enabled(db),
        jd_content=data.jd_content or None,
        target_role=current_user.target_role or None,
        industry=current_user.industry or None,
    )
    result["contact"] = _contact_info(current_user)
    return result


class SaveEnhancedResumeInput(BaseModel):
    resume_id: int | None = None
    title: str = ""
    summary: str
    skills: SkillsInput = SkillsInput()
    experience: list[ExperienceItemInput] = []
    education: list[EducationItemInput] = []
    certifications: list[str] = []
    projects: list[ProjectItemInput] = []
    languages: list[LanguageItemInput] = []
    references: list[str] = []


def _format_raw_text(contact: dict, data: "SaveEnhancedResumeInput") -> str:
    """Builds a well-formatted, plain-text resume from the structured draft —
    a real header (name, title, single-line contact line) followed by
    sections using the exact header phrases resume_structurer.py already
    recognizes ("PROFESSIONAL SUMMARY", "SKILLS", "WORK EXPERIENCE",
    "EDUCATION", "CERTIFICATIONS", "PROJECTS", "LANGUAGES"), so this resume
    parses back out correctly (skills matching, ATS scoring, re-analysis)
    exactly like an uploaded one. Only sections with real content are
    emitted — never an empty heading with nothing under it."""
    lines = []
    if contact.get("full_name"):
        lines.append(contact["full_name"])
    if data.title:
        lines.append(data.title)
    contact_line = " | ".join(filter(None, [
        contact.get("email"), contact.get("phone"), contact.get("location"),
        contact.get("linkedin"), contact.get("portfolio"),
    ]))
    if contact_line:
        lines.append(contact_line)

    if data.summary:
        lines += ["", "PROFESSIONAL SUMMARY", data.summary]

    if data.skills.technical or data.skills.soft:
        lines += ["", "SKILLS"]
        if data.skills.technical:
            lines += ["Technical Skills:"] + [f"• {skill}" for skill in data.skills.technical]
        if data.skills.soft:
            if data.skills.technical:
                lines.append("")
            lines += ["Soft Skills:"] + [f"• {skill}" for skill in data.skills.soft]

    if data.experience:
        lines += ["", "WORK EXPERIENCE"]
        for index, job in enumerate(data.experience):
            if index > 0:
                lines.append("")
            if job.company:
                lines.append(job.company)
            if job.title:
                lines.append(job.title)
            dates = " – ".join(filter(None, [job.start_date, job.end_date]))
            if dates:
                lines.append(dates)
            if job.bullets:
                lines.append("")
                lines += [f"• {bullet}" for bullet in job.bullets]

    if data.education:
        lines += ["", "EDUCATION"]
        for edu in data.education:
            entry = ", ".join(filter(None, [edu.degree, edu.school]))
            lines.append(f"{entry} ({edu.date})" if edu.date else entry)

    if data.certifications:
        lines += ["", "CERTIFICATIONS"]
        lines += [f"• {cert}" for cert in data.certifications]

    if data.projects:
        lines += ["", "PROJECTS"]
        for index, project in enumerate(data.projects):
            if index > 0:
                lines.append("")
            if project.name:
                lines.append(project.name)
            if project.description:
                lines.append(project.description)
            if project.technologies:
                lines.append("Technologies Used: " + ", ".join(project.technologies))
            if project.bullets:
                lines.append("Results Achieved:")
                lines += [f"• {bullet}" for bullet in project.bullets]

    if data.languages:
        lines += ["", "LANGUAGES"]
        lines += [f"• {lang.name} – {lang.proficiency}" if lang.proficiency else f"• {lang.name}" for lang in data.languages]

    if data.references:
        lines += ["", "REFERENCES"]
        lines += [f"• {ref}" for ref in data.references]

    return "\n".join(lines).strip()


@router.post("/save")
def save_enhanced_resume(
    data: SaveEnhancedResumeInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
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

    # Checked before inserting the new row below, to tell a user's first-ever AI
    # build (ai_resume_created) from a later regeneration (ai_resume_regenerated).
    has_prior_ai_build = (
        db.query(Resume).filter(Resume.user_id == current_user.id, Resume.source == "ai_builder").first()
        is not None
    )

    contact = _contact_info(current_user)
    raw_text = _format_raw_text(contact, data)
    all_skills = data.skills.technical + data.skills.soft
    experience_text = "\n".join(
        " | ".join(filter(None, [job.title, job.company, job.start_date, job.end_date])) + "\n"
        + "\n".join(f"- {bullet}" for bullet in job.bullets)
        for job in data.experience
    )
    education_text = "\n".join(
        ", ".join(filter(None, [edu.degree, edu.school, edu.date])) for edu in data.education
    )
    certifications_text = "\n".join(data.certifications)
    projects_text = "\n".join(
        ": ".join(filter(None, [
            project.name, project.description,
            f"Technologies: {', '.join(project.technologies)}" if project.technologies else "",
        ]))
        for project in data.projects
    )

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
        skills=", ".join(all_skills),
        experience=experience_text,
        # Falls back to the source resume's own education/certifications/projects only when
        # the draft genuinely has none — a real chat-built draft's structured entries (even
        # if it only ever produced one) always take precedence over stale prior content.
        education=education_text or (original.education if original else None),
        certifications=certifications_text or (original.certifications if original else None),
        projects=projects_text or (original.projects if original else None),
        version=new_version,
        label=f"v{new_version} (AI-enhanced)" if original else f"v{new_version} (AI-built)",
        is_active=True,
        # Distinguishes this from a plain uploaded resume (the "upload" default) — an existing
        # gap meant totalAiResumeBuilds/related analytics always undercounted, since nothing
        # ever set this explicitly despite the model supporting it.
        source="ai_builder",
    )

    # Exactly one resume can be "active" per user — deactivate every other
    # version, not just the one this save started from.
    db.query(Resume).filter(Resume.user_id == current_user.id).update({Resume.is_active: False})

    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    session_id = get_session_id_from_request(request)
    event_metadata = {"resume_id": new_resume.id, "version": new_resume.version}
    track_event(db, EVENT_TYPES["AI_RESUME_SAVED"], FEATURE_AI_BUILDER, user_id=current_user.id,
                metadata=event_metadata, request=request, session_id=session_id)
    track_event(db, EVENT_TYPES["AI_BUILDER_COMPLETED"], FEATURE_AI_BUILDER, user_id=current_user.id,
                metadata=event_metadata, request=request, session_id=session_id)
    if has_prior_ai_build:
        track_event(db, EVENT_TYPES["AI_RESUME_REGENERATED"], FEATURE_AI_BUILDER, user_id=current_user.id,
                    metadata=event_metadata, request=request, session_id=session_id)
    else:
        track_event(db, EVENT_TYPES["AI_RESUME_CREATED"], FEATURE_AI_BUILDER, user_id=current_user.id,
                    metadata=event_metadata, request=request, session_id=session_id)

    return {
        "message": "Enhanced resume saved as a new version.",
        "resume_id": new_resume.id,
        "version": new_resume.version,
        "label": new_resume.label
    }
