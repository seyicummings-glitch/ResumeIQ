from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import AnalysisResult, Resume, JobDescription, User
from app.services.pdf_report import generate_analysis_pdf
from app.services.analytics import track_event, EVENT_TYPES, FEATURE_DOCUMENTS
from app.security import get_current_user, get_session_id_from_request

router = APIRouter(prefix="/documents", tags=["Documents"])


def _pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    """HTTP header values must be latin-1, but document names can contain
    arbitrary unicode (e.g. an em dash) — RFC 6266's filename* falls back to
    an ASCII-safe `filename` for clients that don't support it."""
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii")
    encoded = quote(filename)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"},
    )


class DocumentGenerateInput(BaseModel):
    analysis_id: int


@router.post("/generate")
def generate_document(
    data: DocumentGenerateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Generates a PDF report for an analysis on demand — called from the "Download PDF
    report" action on Analysis History / Analysis Results. Generated fresh every time rather
    than stored: the standalone Documents page (a saved-file archive) was removed since it only
    ever duplicated this same download, so there's no reason to keep a database record around
    that nothing lists or manages anymore. Both document_generated and document_downloaded fire
    here since, in this architecture, generating a document IS downloading it — there's no
    separate "save for later, download whenever" step."""
    try:
        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.id == data.analysis_id, AnalysisResult.user_id == current_user.id
        ).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found.")

        resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
        job_description = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()

        resume_filename = resume.filename if resume else "Unknown resume"
        jd_title = (job_description.title if job_description and job_description.title else "Analysis")

        pdf_bytes = generate_analysis_pdf(
            analysis=analysis.result_json or {},
            resume_filename=resume_filename,
            jd_title=jd_title,
        )

        session_id = get_session_id_from_request(request)
        event_metadata = {"analysis_id": analysis.id, "doc_type": "analysis-report"}
        track_event(db, EVENT_TYPES["DOCUMENT_GENERATED"], FEATURE_DOCUMENTS, user_id=current_user.id,
                    metadata=event_metadata, request=request, session_id=session_id)
        track_event(db, EVENT_TYPES["DOCUMENT_DOWNLOADED"], FEATURE_DOCUMENTS, user_id=current_user.id,
                    metadata=event_metadata, request=request, session_id=session_id)

        return _pdf_response(pdf_bytes, f"{resume_filename} — {jd_title} Report.pdf")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating document: {str(e)}")
