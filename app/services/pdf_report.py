"""
Pure PDF-rendering function for the "Documents" feature. Takes a plain dict
shaped like AnalysisResult.result_json (see app/services/analysis_store.py
for the shape this is expected to match) and renders a one-page-ish PDF
report using reportlab. No FastAPI/SQLAlchemy imports here — this module is
testable with a plain dict and no app context.
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def _score(value):
    """Best-effort float coercion for score fields that might be missing."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def generate_analysis_pdf(analysis: dict, resume_filename: str, jd_title: str) -> bytes:
    """Render a resume-vs-job-description analysis report as PDF bytes.

    `analysis` is expected to look like:
        {
            "overall_match_score": float,
            "skill_match": {"skill_score": float, "matched_skills": [str], "missing_skills": [str]},
            "experience_match": {"experience_score": float, ...},
            "qualification_match": {"qualification_score": float, ...},
        }
    """
    analysis = analysis or {}
    skill_match = analysis.get("skill_match") or {}
    experience_match = analysis.get("experience_match") or {}
    qualification_match = analysis.get("qualification_match") or {}

    matched_skills = skill_match.get("matched_skills") or []
    missing_skills = skill_match.get("missing_skills") or []

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title="Resume Match Analysis Report",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=20, spaceAfter=4, textColor=colors.HexColor("#1f2937")
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#6b7280"), spaceAfter=16
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], fontSize=13, spaceBefore=16, spaceAfter=8,
        textColor=colors.HexColor("#111827"),
    )
    overall_style = ParagraphStyle(
        "OverallScore", parent=styles["Normal"], fontSize=36, leading=40, textColor=colors.HexColor("#2563eb"),
        spaceAfter=4,
    )
    body_style = styles["Normal"]

    elements = []

    elements.append(Paragraph("Resume Match Analysis Report", title_style))
    generated_on = datetime.now().strftime("%B %d, %Y at %H:%M")
    elements.append(
        Paragraph(
            f"Resume: <b>{resume_filename or 'Unknown resume'}</b> &nbsp;&middot;&nbsp; "
            f"Job: <b>{jd_title or 'Untitled job description'}</b> &nbsp;&middot;&nbsp; "
            f"Generated on {generated_on}",
            subtitle_style,
        )
    )

    overall_score = _score(analysis.get("overall_match_score"))
    elements.append(Paragraph("Overall Match Score", heading_style))
    elements.append(Paragraph(f"{overall_score:.0f}%", overall_style))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Score Breakdown", heading_style))
    breakdown_data = [
        ["Category", "Score"],
        ["Skills", f"{_score(skill_match.get('skill_score')):.0f}%"],
        ["Experience", f"{_score(experience_match.get('experience_score')):.0f}%"],
        ["Qualifications", f"{_score(qualification_match.get('qualification_score')):.0f}%"],
    ]
    breakdown_table = Table(breakdown_data, colWidths=[3 * inch, 2 * inch])
    breakdown_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(breakdown_table)

    elements.append(Paragraph("Matched Skills", heading_style))
    if matched_skills:
        elements.append(Paragraph(", ".join(matched_skills), body_style))
    else:
        elements.append(Paragraph("No matched skills found.", body_style))

    elements.append(Paragraph("Missing Skills", heading_style))
    if missing_skills:
        elements.append(Paragraph(", ".join(missing_skills), body_style))
    else:
        elements.append(Paragraph("No missing skills — great coverage!", body_style))

    doc.build(elements)

    return buffer.getvalue()
