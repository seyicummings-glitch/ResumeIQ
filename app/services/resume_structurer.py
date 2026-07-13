import re

# Common section headers found in resumes (add more as you test with real resumes)
SECTION_HEADERS = {
    "summary": ["summary", "professional summary", "objective", "profile"],
    "skills": ["skills", "technical skills", "core competencies"],
    "experience": ["experience", "work experience", "professional experience", "employment history"],
    "education": ["education", "academic background"],
    "certifications": ["certifications", "certificates", "licenses"],
    "projects": ["projects", "personal projects", "key projects"],
}


def find_section_positions(text: str) -> dict:
    """Find where each known section starts in the text."""
    positions = {}
    lines = text.split("\n")

    for i, line in enumerate(lines):
        clean_line = line.strip().lower().rstrip(":")
        for section, keywords in SECTION_HEADERS.items():
            if clean_line in keywords:
                positions[section] = i

    return positions


def extract_sections(text: str) -> dict:
    lines = text.split("\n")
    positions = find_section_positions(text)

    # Sort sections by where they appear in the text
    sorted_sections = sorted(positions.items(), key=lambda x: x[1])

    result = {key: "" for key in SECTION_HEADERS.keys()}

    for idx, (section, start_line) in enumerate(sorted_sections):
        end_line = sorted_sections[idx + 1][1] if idx + 1 < len(sorted_sections) else len(lines)
        section_content = "\n".join(lines[start_line + 1:end_line]).strip()
        result[section] = section_content

    return result


def extract_contact_info(text: str) -> dict:
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phone_match = re.search(r"(\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
    linkedin_match = re.search(r"linkedin\.com/in/[\w\-]+", text, re.IGNORECASE)

    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
    }


def extract_skills_list(skills_text: str) -> list:
    """Split skills section into individual skills."""
    if not skills_text:
        return []
    skills_text = re.sub(r"[|;•]", ",", skills_text)
    raw_skills = re.split(r"[,\n]", skills_text)
    skills = [s.strip() for s in raw_skills if s.strip() and len(s.strip()) < 40]
    return skills


def structure_resume(text: str) -> dict:
    contact_info = extract_contact_info(text)
    sections = extract_sections(text)
    skills_list = extract_skills_list(sections.get("skills", ""))

    return {
        "contact_info": contact_info,
        "summary": sections.get("summary", ""),
        "skills": skills_list,
        "experience": sections.get("experience", ""),
        "education": sections.get("education", ""),
        "certifications": sections.get("certifications", ""),
        "projects": sections.get("projects", ""),
    }