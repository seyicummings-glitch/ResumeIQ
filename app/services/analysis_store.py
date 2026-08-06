"""
Small query helpers shared by every feature that reads "the user's latest
saved analysis" (skill assessment, interview practice, learning roadmap,
version comparison, admin analytics). Kept separate from matching_engine.py
because it talks to the database — matching_engine.py stays pure functions.
"""
from sqlalchemy.orm import Session
from app.models.models import AnalysisResult


def get_latest_analysis(db: Session, user_id: int, resume_id: int | None = None) -> AnalysisResult | None:
    """Most recently saved AnalysisResult for a user, optionally scoped to one resume."""
    query = db.query(AnalysisResult).filter(AnalysisResult.user_id == user_id)
    if resume_id is not None:
        query = query.filter(AnalysisResult.resume_id == resume_id)
    return query.order_by(AnalysisResult.created_at.desc()).first()
