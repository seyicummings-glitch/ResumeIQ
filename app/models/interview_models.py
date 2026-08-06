from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, LargeBinary
from sqlalchemy.sql import func
from app.database import Base


class InterviewSession(Base):
    """A completed voice mock-interview: the full transcript, the recorded
    audio (if the browser supported capturing it), and the AI-generated
    post-interview feedback report."""
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    jd_title = Column(String, nullable=True)
    transcript_json = Column(JSON, nullable=True)
    audio_data = Column(LargeBinary, nullable=True)
    audio_content_type = Column(String, nullable=True)
    feedback_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
