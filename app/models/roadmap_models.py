from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class LearningRoadmap(Base):
    """A generated, persisted learning roadmap — regenerated on demand (see
    /roadmap/regenerate) rather than rebuilt on every page load, so topic_key
    values stay stable and RoadmapTopicProgress checkmarks survive reloads."""
    __tablename__ = "learning_roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)  # "ai" | "fallback"
    target_role = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    detected_profession = Column(String, nullable=True)
    detected_industry = Column(String, nullable=True)
    stages_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RoadmapTopicProgress(Base):
    __tablename__ = "roadmap_topic_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    roadmap_id = Column(Integer, ForeignKey("learning_roadmaps.id"), nullable=False)
    topic_key = Column(String, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("roadmap_id", "topic_key", name="uq_roadmap_topic"),
    )
