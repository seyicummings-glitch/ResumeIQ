from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import JobDescription, Resume, User
from app.models.roadmap_models import LearningRoadmap, RoadmapTopicProgress
from app.models.skill_assessment_models import SkillAssessmentAttempt
from app.models.interview_models import InterviewSession
from app.security import get_current_user
from app.services.analysis_store import get_latest_analysis
from app.services.resume_structurer import extract_skills_list
from app.services.platform_settings import is_ai_enabled
from app.services.learning_roadmap import build_roadmap
from app.services.learning_roadmap_ai import generate_learning_roadmap
from app.services.skill_resources import fetch_all_resources, get_resource_links

router = APIRouter(prefix="/roadmap", tags=["Learning Roadmap"])


def _skill_assessment_summary(db: Session, user_id: int) -> str | None:
    attempt = (
        db.query(SkillAssessmentAttempt)
        .filter(SkillAssessmentAttempt.user_id == user_id)
        .order_by(SkillAssessmentAttempt.created_at.desc())
        .first()
    )
    if not attempt:
        return None

    breakdown = attempt.category_breakdown or []
    weak = sorted(breakdown, key=lambda item: item.get("pct", 0))[:3]
    weak_text = ", ".join(f"{item.get('category_label', item.get('category_key'))} ({item.get('pct', 0)}%)" for item in weak)
    return (
        f"Technical score: {attempt.technical_score}/100, soft-skill score: {attempt.soft_score}/100. "
        f"Weakest areas: {weak_text or 'none recorded'}."
    )


def _interview_summary(db: Session, user_id: int) -> str | None:
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.desc())
        .first()
    )
    if not session or not session.feedback_json:
        return None

    areas = session.feedback_json.get("areas_to_improve") or []
    if not areas:
        return None
    return "Areas to improve from the most recent mock interview: " + "; ".join(areas[:4])


def _assign_topic_keys(stages: list[dict]) -> list[dict]:
    for stage_index, stage in enumerate(stages):
        for topic_index, topic in enumerate(stage["topics"]):
            topic["topic_key"] = f"{stage_index}-{topic_index}"
    return stages


def _generate_and_save_roadmap(db: Session, current_user: User) -> LearningRoadmap:
    analysis = get_latest_analysis(db, current_user.id)

    resume_text = ""
    resume_skills: list[str] = []
    missing_skills: list[str] = []
    jd_content = ""

    if analysis:
        resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
        resume_text = resume.raw_text or "" if resume else ""
        resume_skills = extract_skills_list(resume.skills or "") if resume else []
        missing_skills = (analysis.result_json or {}).get("skill_match", {}).get("missing_skills", []) or []
        jd = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()
        jd_content = jd.content if jd else ""

    skill_assessment_summary = _skill_assessment_summary(db, current_user.id)
    interview_summary = _interview_summary(db, current_user.id)

    stages_result = None
    if is_ai_enabled(db):
        stages_result = generate_learning_roadmap(
            target_role=current_user.target_role or "",
            industry=current_user.industry or "",
            experience_level=current_user.experience_level or "",
            resume_text=resume_text,
            resume_skills=resume_skills,
            missing_skills=missing_skills,
            jd_content=jd_content,
            skill_assessment_summary=skill_assessment_summary,
            interview_summary=interview_summary,
        )

    source = "ai"
    if stages_result is None:
        stages_result = build_roadmap(
            missing_skills, resume_skills,
            target_role=current_user.target_role, industry=current_user.industry, resume_text=resume_text,
        )
        source = "fallback"

    stages = _assign_topic_keys(stages_result["stages"])

    roadmap = LearningRoadmap(
        user_id=current_user.id,
        source=source,
        target_role=current_user.target_role,
        industry=current_user.industry,
        detected_profession=stages_result.get("detected_profession"),
        detected_industry=stages_result.get("detected_industry"),
        stages_json=stages,
    )
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    return roadmap


def _serialize_roadmap(db: Session, roadmap: LearningRoadmap, user_id: int) -> dict:
    progress_rows = db.query(RoadmapTopicProgress).filter(
        RoadmapTopicProgress.roadmap_id == roadmap.id
    ).all()
    completed_keys = {row.topic_key for row in progress_rows if row.completed}
    all_skill_resources = fetch_all_resources(db)

    total_hours = 0
    done_count = 0
    total_count = 0

    stages = []
    for stage in roadmap.stages_json:
        topics = []
        for topic in stage["topics"]:
            done = topic["topic_key"] in completed_keys
            total_hours += topic.get("estimated_hours", 0)
            total_count += 1
            if done:
                done_count += 1
            resource_links = get_resource_links(topic["title"], all_skill_resources)
            topics.append({**topic, "done": done, "resource_links": resource_links})
        stages.append({**stage, "topics": topics})

    return {
        "roadmap_id": roadmap.id,
        "source": roadmap.source,
        "target_role": roadmap.target_role,
        "industry": roadmap.industry,
        "detected_profession": roadmap.detected_profession,
        "detected_industry": roadmap.detected_industry,
        "stages": stages,
        "created_at": roadmap.created_at,
        "stats": {
            "total_hours": total_hours,
            "done_count": done_count,
            "total_count": total_count,
        },
    }


@router.get("")
def get_roadmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        analysis = get_latest_analysis(db, current_user.id)
        if not current_user.target_role and not analysis:
            return {"has_context": False, "roadmap": None}

        roadmap = (
            db.query(LearningRoadmap)
            .filter(LearningRoadmap.user_id == current_user.id)
            .order_by(LearningRoadmap.created_at.desc())
            .first()
        )
        if not roadmap:
            roadmap = _generate_and_save_roadmap(db, current_user)

        return {"has_context": True, "roadmap": _serialize_roadmap(db, roadmap, current_user.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building roadmap: {str(e)}")


@router.post("/regenerate")
def regenerate_roadmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        analysis = get_latest_analysis(db, current_user.id)
        if not current_user.target_role and not analysis:
            raise HTTPException(
                status_code=400,
                detail="Set a target role in your profile or save an analysis first so the roadmap has context to build from.",
            )

        roadmap = _generate_and_save_roadmap(db, current_user)
        return {"has_context": True, "roadmap": _serialize_roadmap(db, roadmap, current_user.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating roadmap: {str(e)}")


class RoadmapToggleInput(BaseModel):
    topic_key: str


@router.post("/topics/toggle")
def toggle_roadmap_topic(
    data: RoadmapToggleInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        roadmap = (
            db.query(LearningRoadmap)
            .filter(LearningRoadmap.user_id == current_user.id)
            .order_by(LearningRoadmap.created_at.desc())
            .first()
        )
        if not roadmap:
            raise HTTPException(status_code=404, detail="No roadmap found. Load your roadmap first.")

        row = db.query(RoadmapTopicProgress).filter(
            RoadmapTopicProgress.roadmap_id == roadmap.id,
            RoadmapTopicProgress.topic_key == data.topic_key,
        ).first()

        if row:
            row.completed = not row.completed
        else:
            row = RoadmapTopicProgress(
                user_id=current_user.id, roadmap_id=roadmap.id, topic_key=data.topic_key, completed=True
            )
            db.add(row)

        db.commit()
        db.refresh(row)

        return {"topic_key": data.topic_key, "completed": row.completed}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating roadmap progress: {str(e)}")
