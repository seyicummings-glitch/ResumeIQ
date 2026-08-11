from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, JobDescription, AnalysisResult
from app.models.admin_models import Report, AppSetting
from app.security import get_current_user, require_admin
from app.services.admin_analytics import compute_top_missing_skills

# Admin-only routes (user management, reports moderation, analytics, settings).
router = APIRouter(prefix="/admin", tags=["Admin"])

# POST /reports lives outside /admin because any authenticated user (not just
# admins) can file a report.
reports_router = APIRouter(tags=["Reports"])


# ---------------------------------------------------------------------------
# Shared serialization helpers
# ---------------------------------------------------------------------------

def _serialize_report(report: Report, reporter_email: str | None) -> dict:
    return {
        "id": report.id,
        "reporterEmail": reporter_email,
        "reason": report.reason,
        "targetType": report.target_type,
        "targetLabel": report.target_label,
        "status": report.status,
        "createdAt": report.created_at,
    }


def _serialize_settings(row: AppSetting) -> dict:
    return {
        "maintenanceMode": row.maintenance_mode,
        "aiSuggestionsEnabled": row.ai_suggestions_enabled,
        "maxUploadSizeMb": row.max_upload_size_mb,
        "allowedFileTypes": row.allowed_file_types.split(",") if row.allowed_file_types else [],
        "rateLimitPerMinute": row.rate_limit_per_minute,
        "supportEmail": row.support_email,
    }


def _get_or_create_settings(db: Session) -> AppSetting:
    row = db.query(AppSetting).first()
    if not row:
        row = AppSetting()
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class ReportCreateInput(BaseModel):
    reason: str
    targetType: str
    targetLabel: str


@reports_router.post("/reports")
def create_report(
    data: ReportCreateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        report = Report(
            reporter_id=current_user.id,
            reason=data.reason,
            target_type=data.targetType,
            target_label=data.targetLabel,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return _serialize_report(report, current_user.email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating report: {str(e)}")


@router.get("/reports")
def list_reports(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    try:
        rows = (
            db.query(Report, User.email)
            .join(User, User.id == Report.reporter_id)
            .order_by(Report.created_at.desc())
            .all()
        )
        return [_serialize_report(report, email) for report, email in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reports: {str(e)}")


class ReportStatusInput(BaseModel):
    status: str


@router.patch("/reports/{report_id}/status")
def update_report_status(
    report_id: int,
    data: ReportStatusInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        report.status = data.status
        db.commit()
        db.refresh(report)

        reporter = db.query(User).filter(User.id == report.reporter_id).first()
        return _serialize_report(report, reporter.email if reporter else None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating report status: {str(e)}")


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)

        signup_rows = (
            db.query(cast(User.created_at, Date).label("day"), func.count(User.id))
            .filter(User.created_at >= since)
            .group_by("day")
            .order_by("day")
            .all()
        )
        signups_over_time = [{"date": str(day), "signups": count} for day, count in signup_rows]

        analyses_rows = (
            db.query(cast(AnalysisResult.created_at, Date).label("day"), func.count(AnalysisResult.id))
            .filter(AnalysisResult.created_at >= since)
            .group_by("day")
            .order_by("day")
            .all()
        )
        analyses_per_day = [{"date": str(day), "analyses": count} for day, count in analyses_rows]

        score_rows = (
            db.query(cast(AnalysisResult.created_at, Date).label("day"), func.avg(AnalysisResult.match_percentage))
            .filter(AnalysisResult.created_at >= since)
            .group_by("day")
            .order_by("day")
            .all()
        )
        average_score_trend = [
            {"date": str(day), "averageScore": round(avg) if avg is not None else 0}
            for day, avg in score_rows
        ]

        recent_analyses = (
            db.query(AnalysisResult.result_json)
            .order_by(AnalysisResult.created_at.desc())
            .limit(200)
            .all()
        )
        top_missing_skills = compute_top_missing_skills([row[0] for row in recent_analyses], top_n=10)

        total_users = db.query(func.count(User.id)).scalar() or 0
        total_resumes_analyzed = db.query(func.count(AnalysisResult.id)).scalar() or 0
        total_job_descriptions = db.query(func.count(JobDescription.id)).scalar() or 0
        avg_match_score = db.query(func.avg(AnalysisResult.match_percentage)).scalar()

        return {
            "signupsOverTime": signups_over_time,
            "analysesPerDay": analyses_per_day,
            "averageScoreTrend": average_score_trend,
            "topMissingSkills": top_missing_skills,
            "summary": {
                "totalUsers": total_users,
                "totalResumesAnalyzed": total_resumes_analyzed,
                "totalJobDescriptions": total_job_descriptions,
                "averageMatchScore": round(avg_match_score) if avg_match_score is not None else 0,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing analytics: {str(e)}")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@router.get("/settings")
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    try:
        row = _get_or_create_settings(db)
        return _serialize_settings(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching settings: {str(e)}")


class SettingsUpdateInput(BaseModel):
    maintenanceMode: bool | None = None
    aiSuggestionsEnabled: bool | None = None
    maxUploadSizeMb: int | None = None
    allowedFileTypes: list[str] | None = None
    rateLimitPerMinute: int | None = None
    supportEmail: str | None = None


@router.put("/settings")
def update_settings(
    data: SettingsUpdateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        row = _get_or_create_settings(db)

        if data.maintenanceMode is not None:
            row.maintenance_mode = data.maintenanceMode
        if data.aiSuggestionsEnabled is not None:
            row.ai_suggestions_enabled = data.aiSuggestionsEnabled
        if data.maxUploadSizeMb is not None:
            row.max_upload_size_mb = data.maxUploadSizeMb
        if data.allowedFileTypes is not None:
            row.allowed_file_types = ",".join(data.allowedFileTypes)
        if data.rateLimitPerMinute is not None:
            row.rate_limit_per_minute = data.rateLimitPerMinute
        if data.supportEmail is not None:
            row.support_email = data.supportEmail

        db.commit()
        db.refresh(row)
        return _serialize_settings(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")
