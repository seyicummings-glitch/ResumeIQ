import re
from app.services.skill_vocabulary import SKILL_VOCABULARY

# Common section headers found in resumes (English + French/Spanish/German/Portuguese variants)
SECTION_HEADERS = {
    "summary": [
        "summary", "professional summary", "objective", "profile", "about me",
        "résumé", "profil", "objectif professionnel", "sommaire",
        "resumen", "perfil", "objetivo profesional", "objetivo",
        "zusammenfassung", "werdegang", "über mich",
        "resumo", "perfil profissional",
    ],
    "skills": [
        "skills", "technical skills", "core competencies", "key skills",
        "core skills", "tech stack", "technologies", "technical proficiencies",
        "skills & tools", "tools & technologies", "programming languages",
        "compétences", "compétences techniques", "compétences clés",
        "habilidades", "competencias", "competencias técnicas",
        "fähigkeiten", "kenntnisse", "fachkenntnisse",
        "competências", "habilidades técnicas",
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment history",
        "work history", "career history", "relevant experience",
        "expérience", "expérience professionnelle", "parcours professionnel",
        "experiencia", "experiencia laboral", "experiencia profesional",
        "berufserfahrung", "erfahrung",
        "experiência", "experiência profissional",
    ],
    "education": [
        "education", "academic background", "academic qualifications", "qualifications",
        "éducation", "formation", "formation académique", "études",
        "educación", "formación académica",
        "ausbildung", "bildung",
        "educação", "formação acadêmica",
    ],
    "certifications": [
        "certifications", "certificates", "licenses", "certifications & licenses",
        "licenses & certifications", "certifications and licenses",
        "certificats",
        "certificaciones", "certificados",
        "zertifikate", "zertifizierungen",
        "certificações",
    ],
    "projects": [
        "projects", "personal projects", "key projects", "notable projects",
        "projets", "projets personnels",
        "proyectos", "proyectos personales",
        "projekte",
        "projetos", "projetos pessoais",
    ],
}

_MAX_HEADER_LINE_LENGTH = 50


def find_section_positions(text: str) -> dict:
    """Find where each known section starts in the text. Uses a lenient match —
    a short line just needs to contain one of the known header phrases, not
    equal it exactly — since real resumes format headers all sorts of ways
    ("Technical Skills & Tools", "1. Work Experience", "EDUCATION:") that a
    strict exact-line match would silently miss, wrongly reporting a section
    that's genuinely on the resume as "not found"."""
    positions = {}
    lines = text.split("\n")

    for i, line in enumerate(lines):
        clean_line = line.strip().lower().rstrip(":")
        if not clean_line or len(clean_line) > _MAX_HEADER_LINE_LENGTH:
            continue
        for section, keywords in SECTION_HEADERS.items():
            if section in positions:
                continue
            if any(clean_line == kw or kw in clean_line for kw in keywords):
                positions[section] = i
                break

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


# Matches phone-number-shaped digit sequences generally, not just the North
# American "(555) 123-4567" 3-3-4 grouping — real resumes use all sorts of
# international formats (e.g. "+212 6 12 34 56 78", "06 12 34 56 78",
# "+90 532 123 45 67"), and the old strict pattern reported "no phone number"
# on plenty of resumes that genuinely had one.
_PHONE_CANDIDATE_PATTERN = re.compile(r"\+?\(?\d[\d\s().\-]{6,}\d")


def _find_phone(text: str) -> str | None:
    for match in _PHONE_CANDIDATE_PATTERN.finditer(text):
        candidate = match.group(0)
        digit_count = sum(c.isdigit() for c in candidate)
        if 8 <= digit_count <= 15:
            return candidate.strip()
    return None


def extract_contact_info(text: str) -> dict:
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    linkedin_match = re.search(r"linkedin\.com/in/[\w\-]+", text, re.IGNORECASE)
    github_match = re.search(r"github\.com/([\w\-]+)", text, re.IGNORECASE)

    return {
        "email": email_match.group(0) if email_match else None,
        "phone": _find_phone(text),
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
        "github": github_match.group(1) if github_match else None,
    }


def extract_skills_list(skills_text: str) -> list:
    """Split skills section into individual skills."""
    if not skills_text:
        return []
    skills_text = re.sub(r"[|;•]", ",", skills_text)
    raw_skills = re.split(r"[,\n]", skills_text)
    skills = [s.strip() for s in raw_skills if s.strip() and len(s.strip()) < 40]
    return skills


def extract_vocabulary_skills(text: str) -> list:
    """Finds real, named skills anywhere in the resume text — not just inside a
    labeled Skills section. Candidates often mention skills in experience
    bullets, project descriptions, or a summary without a dedicated section
    (or under a header like "Tech Stack"/"Core Competencies" that a strict
    section-header match won't recognize) — without this, matching would
    wrongly report a skill as "missing" when it's genuinely on the resume."""
    text_lower = text.lower()
    return [
        skill
        for skill in SKILL_VOCABULARY
        if re.search(r"(?<![a-zA-Z0-9])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])", text_lower)
    ]


def structure_resume(text: str) -> dict:
    contact_info = extract_contact_info(text)
    sections = extract_sections(text)
    section_skills = extract_skills_list(sections.get("skills", ""))

    # Merge in vocabulary-recognized skills found anywhere else in the resume that
    # the labeled Skills section (if any) didn't already list, preserving the
    # candidate's own phrasing for anything the Skills section did list.
    section_skills_lower = {s.lower() for s in section_skills}
    skills_list = section_skills + [
        skill for skill in extract_vocabulary_skills(text) if skill.lower() not in section_skills_lower
    ]

    return {
        "contact_info": contact_info,
        "summary": sections.get("summary", ""),
        "skills": skills_list,
        "experience": sections.get("experience", ""),
        "education": sections.get("education", ""),
        "certifications": sections.get("certifications", ""),
        "projects": sections.get("projects", ""),
    }