"""
Rule-based ATS (Applicant Tracking System) compatibility scorer.

Answers a different question than matching_engine.py: not "does this resume
fit a specific job?" but "would a real-world ATS (Workday, Greenhouse,
Taleo, iCIMS, etc.) successfully parse this resume's content at all?"
No job description is involved - this is a standalone resume analysis.

No machine learning or AI is used - every score is a deterministic
bucketed/weighted calculation over already-parsed resume text and
structure. Final score is a weighted sum out of 100:

    overall_ats_score = contact_score (15)
                       + section_score (25)
                       + skills_score (20)
                       + extraction_score (25)
                       + format_score (15)

Note on file-format risk vs text-extraction health: resume_parser.py
already OCR-recovers scanned PDFs/images before this scorer ever sees the
text, so a well-OCR'd scanned resume can still score well on extraction
health. file-format risk exists specifically to flag that risk anyway -
most production ATS do not run OCR, so an image upload is penalized here
regardless of how well our own pipeline happened to read it.
"""

FORMAT_RISK_SCORES = {
    ".docx": 15,
    ".pdf": 13,
    ".txt": 10,
    ".png": 0,
    ".jpg": 0,
    ".jpeg": 0,
}


def score_contact_completeness(contact_info: dict) -> dict:
    """Score email/phone/linkedin presence (max 15: email=8, phone=5, linkedin=2)."""
    score = 0
    issues = []

    if contact_info.get("email"):
        score += 8
    else:
        issues.append("No email address detected.")

    if contact_info.get("phone"):
        score += 5
    else:
        issues.append("No phone number detected.")

    if contact_info.get("linkedin"):
        score += 2
    else:
        issues.append("No LinkedIn profile detected.")

    return {"contact_score": score, "issues": issues}


def score_section_completeness(structured_data: dict) -> dict:
    """Score presence of standard resume sections (max 25, weighted by ATS reliance on each)."""
    weights = {
        "experience": 8,
        "education": 6,
        "skills": 6,
        "summary": 3,
        "certifications": 1,
        "projects": 1,
    }
    score = 0
    issues = []

    for section, points in weights.items():
        if section == "skills":
            present = bool(structured_data.get("skills"))
        else:
            present = bool(str(structured_data.get(section, "")).strip())

        if present:
            score += points
        else:
            issues.append(f"No {section.capitalize()} section found.")

    return {"section_score": score, "issues": issues}


def score_skills_detected(skills: list) -> dict:
    """Score number of detected skills (max 20, bucketed: 0/1-4/5-9/10+)."""
    count = len(skills)
    issues = []

    if count == 0:
        score = 0
        issues.append("No skills detected - ATS keyword matching will likely fail.")
    elif count < 5:
        score = 10
        issues.append("Very few skills detected - consider listing more relevant skills.")
    elif count < 10:
        score = 15
    else:
        score = 20

    return {"skills_score": score, "skills_count": count, "issues": issues}


def score_text_extraction_health(resume_text: str) -> dict:
    """Score extracted text length as a proxy for clean parseability (max 25)."""
    length = len(resume_text.strip())
    issues = []

    if length < 30:
        score = 0
        issues.append("Almost no text could be extracted - resume may be a scanned image or corrupted file.")
    elif length < 500:
        score = 10
        issues.append("Very little text extracted - resume may use complex formatting (tables, columns, graphics) that ATS systems struggle to parse.")
    elif length < 1500:
        score = 20
    else:
        score = 25

    return {"extraction_score": score, "character_count": length, "issues": issues}


def score_file_format_risk(filename: str) -> dict:
    """Score file format's real-world ATS parseability risk (max 15)."""
    filename_lower = filename.lower()
    extension = "." + filename_lower.rsplit(".", 1)[-1] if "." in filename_lower else ""
    score = FORMAT_RISK_SCORES.get(extension, 0)
    issues = []

    if extension in (".png", ".jpg", ".jpeg"):
        issues.append("Image file format - most ATS systems cannot extract text from images at all. Submit a .docx or .pdf instead.")
    elif extension == ".txt":
        issues.append(".txt is parseable but many employer application portals don't accept plain text uploads.")

    return {"format_score": score, "file_extension": extension, "issues": issues}


def calculate_ats_score(filename: str, resume_text: str, structured_data: dict) -> dict:
    """Combine all sub-scores into a weighted 0-100 ATS compatibility score."""
    contact = score_contact_completeness(structured_data.get("contact_info", {}))
    sections = score_section_completeness(structured_data)
    skills = score_skills_detected(structured_data.get("skills", []))
    extraction = score_text_extraction_health(resume_text)
    file_format = score_file_format_risk(filename)

    overall = (
        contact["contact_score"]
        + sections["section_score"]
        + skills["skills_score"]
        + extraction["extraction_score"]
        + file_format["format_score"]
    )

    all_issues = (
        contact["issues"]
        + sections["issues"]
        + skills["issues"]
        + extraction["issues"]
        + file_format["issues"]
    )

    return {
        "overall_ats_score": overall,
        "contact_completeness": contact,
        "section_completeness": sections,
        "skills_detected": skills,
        "text_extraction_health": extraction,
        "file_format_risk": file_format,
        "issues": all_issues,
    }
