from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    doc_type = Column(String, nullable=False, default="analysis-report")
    analysis_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=True)
    size_kb = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
