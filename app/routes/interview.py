import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Resume, JobDescription, User
from app.models.interview_models import InterviewSession
from app.security import get_current_user, get_session_id_from_request
from app.services.analysis_store import get_latest_analysis
from app.services.resume_structurer import extract_skills_list
from app.services.interview_questions import (
    BEHAVIORAL_BASE,
    build_interview_questions,
    build_system_design_questions,
    build_role_questions,
)
from app.services.ai_interviewer import get_interviewer_reply
from app.services.interview_feedback import generate_interview_feedback
from app.services.platform_settings import is_ai_enabled
from app.services.analytics import track_event, EVENT_TYPES, FEATURE_INTERVIEW

router = APIRouter(prefix="/interview", tags=["Interview Practice"])


def _context_for_user(db: Session, user_id: int):
    """Resume text, JD content/title, and missing/resume skills from the
    user's latest saved analysis — shared by /questions and /chat so both
    stay in sync with the same underlying data."""
    analysis = get_latest_analysis(db, user_id)
    if not analysis:
        return None

    result_json = analysis.result_json or {}
    missing_skills = result_json.get("skill_match", {}).get("missing_skills", [])

    resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
    resume_skills = extract_skills_list(resume.skills or "") if resume else []
    resume_text = resume.raw_text if resume else ""

    job_description = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()
    jd_title = job_description.title if job_description and job_description.title else ""
    jd_content = job_description.content if job_description else ""

    return {
        "resume_text": resume_text,
        "resume_skills": resume_skills,
        "jd_title": jd_title,
        "jd_content": jd_content,
        "missing_skills": missing_skills,
    }


@router.get("/questions")
def get_interview_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    context = _context_for_user(db, current_user.id)

    if not context:
        questions = list(BEHAVIORAL_BASE) + build_system_design_questions("") + build_role_questions("")
        return {"questions": questions, "has_analysis": False}

    questions = build_interview_questions(context["missing_skills"], context["resume_skills"], context["jd_title"])
    return {"questions": questions, "has_analysis": True, "jd_title": context["jd_title"]}


class InterviewChatMessage(BaseModel):
    role: str  # "interviewer" | "candidate"
    content: str


class InterviewChatInput(BaseModel):
    conversation: list[InterviewChatMessage] = []
    preferred_language: str | None = None
    mode: str | None = None  # "voice" | "text" — only meaningful/known on the first turn


@router.post("/chat")
def post_interview_chat(
    data: InterviewChatInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Turn-by-turn AI mock interview. The frontend keeps the running
    transcript client-side and resends it in full each turn — no server-side
    session state to manage."""
    context = _context_for_user(db, current_user.id)
    if not context:
        raise HTTPException(
            status_code=404,
            detail="Save an analysis from your dashboard first so the interview can be tailored to your resume and the job."
        )

    conversation = [m.model_dump() for m in data.conversation]
    session_id = get_session_id_from_request(request)

    if not conversation:
        # An empty conversation is the de facto "start" of an interview — there's no
        # explicit start/end handshake in this stateless, resend-the-transcript design.
        track_event(db, EVENT_TYPES["INTERVIEW_STARTED"], FEATURE_INTERVIEW, user_id=current_user.id,
                    metadata={"mode": data.mode}, request=request, session_id=session_id)
        if data.mode == "voice":
            track_event(db, EVENT_TYPES["VOICE_INTERVIEW_STARTED"], FEATURE_INTERVIEW, user_id=current_user.id,
                        request=request, session_id=session_id)
        elif data.mode == "text":
            track_event(db, EVENT_TYPES["TEXT_INTERVIEW_STARTED"], FEATURE_INTERVIEW, user_id=current_user.id,
                        request=request, session_id=session_id)
    else:
        track_event(db, EVENT_TYPES["FOLLOWUP_GENERATED"], FEATURE_INTERVIEW, user_id=current_user.id,
                    metadata={"turn": len(conversation)}, request=request, session_id=session_id)

    result = get_interviewer_reply(
        resume_text=context["resume_text"],
        jd_content=context["jd_content"],
        jd_title=context["jd_title"],
        missing_skills=context["missing_skills"],
        resume_skills=context["resume_skills"],
        conversation=conversation,
        ai_enabled=is_ai_enabled(db),
        preferred_language=data.preferred_language,
    )

    return result


@router.post("/sessions")
async def save_interview_session(
    transcript: str = Form(...),
    audio: UploadFile | None = File(None),
    mode: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Called once, when a voice interview ends: persists the transcript and
    recorded audio (if the browser supported capturing it), and generates a
    post-interview feedback report over the full conversation."""
    try:
        transcript_list = json.loads(transcript)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid transcript JSON.")

    context = _context_for_user(db, current_user.id)
    resume_text = context["resume_text"] if context else ""
    jd_title = context["jd_title"] if context else ""
    jd_content = context["jd_content"] if context else ""
    missing_skills = context["missing_skills"] if context else []

    feedback = generate_interview_feedback(
        transcript=transcript_list,
        resume_text=resume_text,
        jd_title=jd_title,
        jd_content=jd_content,
        missing_skills=missing_skills,
        ai_enabled=is_ai_enabled(db),
    )

    audio_bytes = None
    audio_content_type = None
    if audio is not None:
        audio_bytes = await audio.read()
        audio_content_type = audio.content_type

    session = InterviewSession(
        user_id=current_user.id,
        jd_title=jd_title,
        transcript_json=transcript_list,
        audio_data=audio_bytes,
        audio_content_type=audio_content_type,
        feedback_json=feedback,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    session_id = get_session_id_from_request(request)
    # `mode` reflects what the frontend was actually running (falls back to inferring
    # from audio presence for older clients that don't send it explicitly).
    resolved_mode = mode or ("voice" if audio_bytes is not None else "text")
    track_event(
        db, EVENT_TYPES["INTERVIEW_COMPLETED"], FEATURE_INTERVIEW, user_id=current_user.id,
        metadata={"session_id": session.id, "mode": resolved_mode, "has_audio": audio_bytes is not None},
        request=request, session_id=session_id,
    )
    track_event(
        db, EVENT_TYPES["INTERVIEW_FEEDBACK_GENERATED"], FEATURE_INTERVIEW, user_id=current_user.id,
        metadata={"session_id": session.id}, request=request, session_id=session_id,
    )

    return {
        "id": session.id,
        "feedback": feedback,
        "has_audio": audio_bytes is not None,
    }


@router.get("/sessions")
def list_interview_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "jd_title": row.jd_title,
            "created_at": row.created_at,
            "has_audio": row.audio_data is not None,
            "overall_assessment": (row.feedback_json or {}).get("overall_assessment"),
        }
        for row in rows
    ]


@router.get("/sessions/{session_id}")
def get_interview_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id, InterviewSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    return {
        "id": session.id,
        "jd_title": session.jd_title,
        "created_at": session.created_at,
        "transcript": session.transcript_json,
        "feedback": session.feedback_json,
        "has_audio": session.audio_data is not None,
    }


@router.get("/sessions/{session_id}/audio")
def get_interview_session_audio(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id, InterviewSession.user_id == current_user.id
    ).first()
    if not session or not session.audio_data:
        raise HTTPException(status_code=404, detail="Recording not found.")

    return Response(content=session.audio_data, media_type=session.audio_content_type or "audio/webm")
