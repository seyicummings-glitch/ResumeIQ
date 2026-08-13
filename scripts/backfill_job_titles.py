"""
One-off backfill: sets JobDescription.title for existing rows saved without one, using the
same AI title-extraction that already runs on every analysis (see
app/services/job_description_ai.py, JD_SCHEMA's "title" field) instead of guessing from raw text.

Safe to re-run — only touches rows where title is still NULL/empty.
"""
from app.database import SessionLocal
from app.models.models import JobDescription
from app.services.job_description_ai import parse_job_description_ai
from app.services.job_description_parser import derive_job_title


def run_backfill():
    db = SessionLocal()
    try:
        job_descriptions = (
            db.query(JobDescription)
            .filter((JobDescription.title.is_(None)) | (JobDescription.title == ""))
            .all()
        )
        print(f"Found {len(job_descriptions)} job description(s) without a title.")

        updated = 0
        for jd in job_descriptions:
            ai_result = parse_job_description_ai(jd.content, ai_enabled=True)
            title = (ai_result or {}).get("title") or ""
            if not title:
                title = derive_job_title(None, jd.content)
            jd.title = title
            updated += 1
            print(f"  JobDescription {jd.id}: -> {title!r}".encode("ascii", "replace").decode())

        db.commit()
        print(f"Backfilled {updated} job description(s).")
    finally:
        db.close()


if __name__ == "__main__":
    run_backfill()
