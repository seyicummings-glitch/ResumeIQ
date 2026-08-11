from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, Resume, AnalysisResult
from app.models.interview_models import InterviewSession
from app.models.skill_assessment_models import SkillAssessmentAttempt
from app.models.roadmap_models import LearningRoadmap
from app.models.document_models import GeneratedDocument
from app.security import require_admin
from app.services.pagination import paginate, page_response

router = APIRouter(prefix="/admin/users", tags=["Admin - Users"])


def _serialize_user(db: Session, user: User) -> dict:
    resumes_count = db.query(func.count(Resume.id)).filter(Resume.user_id == user.id).scalar() or 0
    analyses_count = db.query(func.count(AnalysisResult.id)).filter(AnalysisResult.user_id == user.id).scalar() or 0
    return {
        "id": user.id,
        "email": user.email,
        "fullName": user.full_name,
        "role": user.role,
        "status": user.status,
        "country": user.country,
        "lastLoginAt": user.last_login_at,
        "createdAt": user.created_at,
        "resumesCount": resumes_count,
        "totalActivity": resumes_count + analyses_count,
    }


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        query = db.query(User)
        if search:
            like = f"%{search}%"
            query = query.filter(or_(User.email.ilike(like), User.full_name.ilike(like)))
        if status and status != "all":
            query = query.filter(User.status == status)
        if role and role != "all":
            query = query.filter(User.role == role)

        query = query.order_by(User.id)
        items, total = paginate(query, page, pageSize)
        return page_response([_serialize_user(db, user) for user in items], total, page, pageSize)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@router.get("/{user_id}")
def get_user_detail(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    counts = {
        "resumes": db.query(func.count(Resume.id)).filter(Resume.user_id == user.id).scalar() or 0,
        "analyses": db.query(func.count(AnalysisResult.id)).filter(AnalysisResult.user_id == user.id).scalar() or 0,
        "interviewSessions": db.query(func.count(InterviewSession.id)).filter(InterviewSession.user_id == user.id).scalar() or 0,
        "skillAssessments": db.query(func.count(SkillAssessmentAttempt.id)).filter(SkillAssessmentAttempt.user_id == user.id).scalar() or 0,
        "learningRoadmaps": db.query(func.count(LearningRoadmap.id)).filter(LearningRoadmap.user_id == user.id).scalar() or 0,
        "documents": db.query(func.count(GeneratedDocument.id)).filter(GeneratedDocument.user_id == user.id).scalar() or 0,
    }

    return {**_serialize_user(db, user), "counts": counts}


class UserUpdateInput(BaseModel):
    fullName: str | None = None
    role: str | None = None
    country: str | None = None


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if data.fullName is not None:
            user.full_name = data.fullName
        if data.role is not None:
            user.role = data.role
        if data.country is not None:
            user.country = data.country

        db.commit()
        db.refresh(user)
        return _serialize_user(db, user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")


class UserStatusInput(BaseModel):
    status: str


@router.patch("/{user_id}/status")
def set_user_status(
    user_id: int,
    data: UserStatusInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.status = data.status
        db.commit()
        db.refresh(user)
        return _serialize_user(db, user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user status: {str(e)}")


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Soft delete only: marks the account status='deleted' and blocks login (see
    app/routes/auth.py's login()). All historical data (resumes, analyses, etc.)
    is left intact since related tables have no cascade configured."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account.")

        user.status = "deleted"
        db.commit()
        db.refresh(user)
        return _serialize_user(db, user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")
