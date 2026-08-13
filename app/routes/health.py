from datetime import datetime, timezone
import os
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin_models import AppSetting

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    force_maintenance = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
        setting = db.query(AppSetting).first()
        maintenance = force_maintenance or bool(setting and setting.maintenance_mode)
    except Exception:
        database_status = "unreachable"
        maintenance = force_maintenance

    if maintenance:
        status = "maintenance"
    elif database_status == "connected":
        status = "ok"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "database": database_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
