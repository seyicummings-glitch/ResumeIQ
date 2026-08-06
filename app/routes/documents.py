from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import AnalysisResult, Resume, JobDescription, User
from app.models.document_models import GeneratedDocument
from app.services.pdf_report import generate_analysis_pdf
from app.security import get_current_user

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


def _load_report_inputs(db: Session, analysis_id: int, user_id: int):
    """Load an AnalysisResult (ownership-checked) plus its Resume and JobDescription."""
    analysis = db.query(AnalysisResult).filter(
        AnalysisResult.id == analysis_id, AnalysisResult.user_id == user_id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
    job_description = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()

    return analysis, resume, job_description


class DocumentGenerateInput(BaseModel):
    analysis_id: int


@router.post("/generate")
def generate_document(
    data: DocumentGenerateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        analysis, resume, job_description = _load_report_inputs(db, data.analysis_id, current_user.id)

        resume_filename = resume.filename if resume else "Unknown resume"
        jd_title = (job_description.title if job_description and job_description.title else "Analysis")

        pdf_bytes = generate_analysis_pdf(
            analysis=analysis.result_json or {},
            resume_filename=resume_filename,
            jd_title=jd_title,
        )

        document = GeneratedDocument(
            user_id=current_user.id,
            name=f"{resume_filename} — {jd_title} Report.pdf",
            doc_type="analysis-report",
            analysis_id=analysis.id,
            size_kb=round(len(pdf_bytes) / 1024),
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        return _pdf_response(pdf_bytes, document.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating document: {str(e)}")


@router.get("")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(GeneratedDocument)
        .filter(GeneratedDocument.user_id == current_user.id)
        .order_by(GeneratedDocument.created_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "doc_type": row.doc_type,
            "analysis_id": row.analysis_id,
            "size_kb": row.size_kb,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        document = db.query(GeneratedDocument).filter(
            GeneratedDocument.id == document_id, GeneratedDocument.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")

        if document.analysis_id is None:
            raise HTTPException(status_code=404, detail="This document has no linked analysis to regenerate from.")

        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.id == document.analysis_id, AnalysisResult.user_id == current_user.id
        ).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="The underlying analysis for this document was deleted.")

        resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
        job_description = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()

        resume_filename = resume.filename if resume else "Unknown resume"
        jd_title = (job_description.title if job_description and job_description.title else "Analysis")

        pdf_bytes = generate_analysis_pdf(
            analysis=analysis.result_json or {},
            resume_filename=resume_filename,
            jd_title=jd_title,
        )

        return _pdf_response(pdf_bytes, document.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading document: {str(e)}")


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        document = db.query(GeneratedDocument).filter(
            GeneratedDocument.id == document_id, GeneratedDocument.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")

        db.delete(document)
        db.commit()

        return {"message": "Document deleted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
