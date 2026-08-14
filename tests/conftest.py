"""Shared pytest fixtures. `db_session` spins up a throwaway in-memory SQLite
database with the full schema, for unit-testing service functions that take a
live `db: Session` (e.g. admin dashboard/pagination aggregation) without
touching the real Postgres database."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
# Import every model module so their tables register on Base.metadata before create_all.
from app.models import models, admin_models, document_models, interview_models, roadmap_models, skill_assessment_models, ai_conversation_models, subscription_models, skill_resource_models, analytics_models  # noqa: F401


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


@pytest.fixture(autouse=True)
def _no_real_dns_lookups(monkeypatch):
    """Registration's email deliverability check (app.schemas.validate_reachable_email)
    does a real DNS lookup — unit tests never do real network I/O, so this is patched
    to a no-op everywhere by default, keeping fictional test domains like example.com
    working exactly like before. A test that wants to exercise the rejection path can
    still override this with its own monkeypatch.setattr on check_email_deliverable."""
    import app.schemas as schemas_module

    monkeypatch.setattr(schemas_module, "check_email_deliverable", lambda *args, **kwargs: None)
