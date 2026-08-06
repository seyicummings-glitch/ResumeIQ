from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class SkillQuestion(Base):
    """Static multiple-choice question bank — used only as the no-AI fallback
    (see app/services/skill_assessment_ai.py). The primary path generates
    open-ended questions on the fly via Gemini instead of reading this table."""
    __tablename__ = "skill_questions"

    id = Column(Integer, primary_key=True, index=True)
    category_key = Column(String, index=True, nullable=False)
    category_label = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)  # "beginner" | "intermediate" | "advanced"
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # list of 4 strings
    correct_index = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=False)
    tip = Column(Text, nullable=False)


class SkillAssessmentSession(Base):
    """One built-but-not-yet-submitted assessment: the exact 15 questions shown
    to the user, including the hidden grading rubric (expected_answer_points /
    correct_index) that /submit grades against. Storing this server-side — rather
    than trusting whatever the client posts back — is what makes grading tamper-proof
    and lets AI-mode questions carry a free-text rubric instead of a multiple-choice
    correct_index."""
    __tablename__ = "skill_assessment_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)  # "ai" | "fallback"
    questions_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SkillAssessmentAttempt(Base):
    __tablename__ = "skill_assessment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("skill_assessment_sessions.id"), nullable=True)
    source = Column(String, nullable=True)  # "ai" | "fallback"
    technical_score = Column(Integer, nullable=False)
    soft_score = Column(Integer, nullable=False)
    overall_score = Column(Integer, nullable=False)
    category_breakdown = Column(JSON, nullable=True)  # list of {category_key, category_label, correct, total, pct}
    question_feedback = Column(JSON, nullable=True)  # list of per-question {question, answer, score, is_correct, explanation, correct_answer, category, type}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
