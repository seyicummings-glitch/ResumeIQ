"""Shared pytest fixtures. `db_session` spins up a throwaway in-memory SQLite
database with the full schema, for unit-testing service functions that take a
live `db: Session` (e.g. admin dashboard/pagination aggregation) without
touching the real Postgres database."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
# Import every model module so their tables register on Base.metadata before create_all.
from app.models import models, admin_models, document_models, interview_models, roadmap_models, skill_assessment_models, ai_conversation_models, subscription_models, skill_resource_models  # noqa: F401


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
