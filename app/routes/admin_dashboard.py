from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.security import require_admin
from app.services.admin_dashboard import compute_dashboard_summary
from app.services.analytics_reporting import get_activity_feed

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    try:
        return compute_dashboard_summary(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing dashboard: {str(e)}")


@router.get("/activity-feed")
def get_activity_feed_route(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Live feed of the most recent platform activity across every user,
    newest first — polled by the admin dashboard for real-time updates (see
    the frontend's refetchInterval) rather than pushed over a WebSocket."""
    try:
        return {"activity": get_activity_feed(db, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading activity feed: {str(e)}")
