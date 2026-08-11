from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class SkillResource(Base):
    """Admin-curated learning links for a skill, surfaced on the Learning
    Roadmap so a missing skill comes with somewhere to actually go learn it,
    not just a name. Looked up by skill_key (see
    app/services/skill_resources.py's normalize_skill_key) against a topic's
    title — when no row matches, the roadmap falls back to generated search
    links instead of leaving the skill without any resources at all."""
    __tablename__ = "skill_resources"

    id = Column(Integer, primary_key=True, index=True)
    skill_key = Column(String, unique=True, nullable=False, index=True)
    skill_label = Column(String, nullable=False)
    youtube_url = Column(String, nullable=True)
    course_url = Column(String, nullable=True)
    docs_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
