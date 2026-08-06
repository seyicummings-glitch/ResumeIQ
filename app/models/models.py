from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user", nullable=False)
    status = Column(String, default="active", nullable=False)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    target_role = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    career_goals = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resumes = relationship("Resume", back_populates="owner")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    education = Column(Text, nullable=True)
    certifications = Column(Text, nullable=True)
    projects = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    label = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    file_data = Column(LargeBinary, nullable=True)
    file_content_type = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="resumes")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    match_percentage = Column(Integer, nullable=True)
    matched_keywords = Column(Text, nullable=True)
    missing_keywords = Column(Text, nullable=True)
    result_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())