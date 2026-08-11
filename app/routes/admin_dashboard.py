from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.security import require_admin
from app.services.admin_dashboard import compute_dashboard_summary

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    try:
        return compute_dashboard_summary(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing dashboard: {str(e)}")
