"""
One-off, idempotent schema migration for changes that `Base.metadata.create_all`
can't apply on its own (it only creates missing tables/columns on tables that
don't exist yet — it never ALTERs or drops columns on an existing table).
This project has no Alembic, so column additions/removals on pre-existing
tables (analysis_results, resumes, users) are done here instead.

Safe to re-run: every statement uses `ADD COLUMN IF NOT EXISTS` or
`DROP COLUMN IF EXISTS`.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

STATEMENTS = [
    # Milestone 0 — persist real analyses
    "ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
    "ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS result_json JSON",
    # Milestone 5 — resume version history
    "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS label VARCHAR",
    "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
    # Milestone 7 — admin: user status
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active'",
    # Rich profile
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS location VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS github_url VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS portfolio_url VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS target_role VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS industry VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS experience_level VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS career_goals TEXT",
    # Resume dashboard — store the original uploaded file so it can be re-downloaded
    "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_data BYTEA",
    "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_content_type VARCHAR",
    # Skill assessment rework — AI-generated/graded sessions instead of a static MC bank
    "ALTER TABLE skill_assessment_attempts ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES skill_assessment_sessions(id)",
    "ALTER TABLE skill_assessment_attempts ADD COLUMN IF NOT EXISTS source VARCHAR",
    "ALTER TABLE skill_assessment_attempts ADD COLUMN IF NOT EXISTS question_feedback JSON",
    # Admin panel Wave 1 — user profile/activity fields, resume provenance
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR DEFAULT 'free'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ",
    "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'upload'",
    # Profession-aware learning roadmaps — persist what was actually detected
    "ALTER TABLE learning_roadmaps ADD COLUMN IF NOT EXISTS detected_profession VARCHAR",
    "ALTER TABLE learning_roadmaps ADD COLUMN IF NOT EXISTS detected_industry VARCHAR",
    # Rich video/course cards for skill resources
    "ALTER TABLE skill_resources ADD COLUMN IF NOT EXISTS youtube_title VARCHAR",
    "ALTER TABLE skill_resources ADD COLUMN IF NOT EXISTS youtube_channel VARCHAR",
    "ALTER TABLE skill_resources ADD COLUMN IF NOT EXISTS youtube_duration VARCHAR",
    "ALTER TABLE skill_resources ADD COLUMN IF NOT EXISTS course_title VARCHAR",
    "ALTER TABLE skill_resources ADD COLUMN IF NOT EXISTS course_provider VARCHAR",
    # Subscription & credit management — transactions now cover both plan
    # charges and credit-package purchases (see app/models/subscription_models.py)
    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS kind VARCHAR NOT NULL DEFAULT 'subscription'",
    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS payment_method VARCHAR",
    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS credits_purchased INTEGER",
    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS external_reference VARCHAR",
    # AI Resume Builder conversation history — a user can now have multiple conversations per
    # kind (New Chat + switch back to any past one), so the old one-row-per-(user,kind)
    # uniqueness no longer holds.
    "ALTER TABLE ai_conversations DROP CONSTRAINT IF EXISTS uq_ai_conversation_user_kind",
    "ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS title VARCHAR",
    "ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()",
    # AI token economy — shared token balance (was: per-plan daily/monthly usage counters only).
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS monthly_credits INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE credit_balances ADD COLUMN IF NOT EXISTS last_free_refresh_at TIMESTAMPTZ",
    "ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS free_signup_credits INTEGER NOT NULL DEFAULT 100",
    "ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS free_credit_refresh_hours INTEGER NOT NULL DEFAULT 720",
]


def run_migration():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set.")

    engine = create_engine(database_url)
    with engine.begin() as conn:
        for statement in STATEMENTS:
            print(f"Running: {statement}")
            conn.execute(text(statement))

    print("Migration complete.")


if __name__ == "__main__":
    run_migration()
