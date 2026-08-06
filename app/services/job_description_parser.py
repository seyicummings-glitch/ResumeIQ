import re
from collections import Counter
from app.services.skill_vocabulary import SKILL_VOCABULARY


EXPERIENCE_PATTERN = re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience", re.IGNORECASE)

QUALIFICATION_KEYWORDS = [
    "bachelor", "master", "phd", "degree", "certification", "certified",
    "diploma", "b.sc", "m.sc", "b.tech", "m.tech", "j.d.", "jd", "md",
    "license", "licensed", "associate degree", "high school"
]

STOPWORDS = {
    "the", "and", "for", "with", "you", "our", "are", "will", "have",
    "this", "that", "your", "from", "who", "what", "role", "job",
    "we", "a", "an", "to", "of", "in", "on", "as", "is", "be", "at",
    "or", "must", "should", "can", "not", "all", "any", "also", "into",
    "such", "than", "then", "them", "they", "their", "there", "these",
    "those", "it", "its", "by", "if", "but", "so", "up", "out", "about"
}


def extract_required_skills(text: str) -> list:
    """Primarily matches the JD against a curated vocabulary of real, named
    skills — not just the most frequent words in the text, which produced
    generic, meaningless "skills" (e.g. "responsible", "opportunity") whenever
    two JDs shared similar boilerplate phrasing. The vocabulary skews technical,
    so for domains it barely covers (law, healthcare, sales, ...) this
    supplements with the JD's own distinctive frequent terms rather than
    returning next to nothing."""
    text_lower = text.lower()
    matched = [
        skill.lower()
        for skill in SKILL_VOCABULARY
        if re.search(r"(?<![a-zA-Z0-9])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])", text_lower)
    ]

    if len(matched) >= 3:
        return sorted(set(matched))

    text_clean = re.sub(r"[^a-zA-Z0-9\s\-]", " ", text_lower)
    words = text_clean.split()
    candidate_terms = [w for w in words if len(w) > 3 and w not in STOPWORDS]
    word_counts = Counter(candidate_terms)
    top_terms = [word for word, _ in word_counts.most_common(25) if word not in matched]

    return sorted(set(matched + top_terms))


def extract_experience_level(text: str) -> str:
    match = EXPERIENCE_PATTERN.search(text)
    if match:
        return f"{match.group(1)}+ years"
    return "Not specified"


def extract_qualifications(text: str) -> list:
    text_lower = text.lower()
    found = [kw for kw in QUALIFICATION_KEYWORDS if kw in text_lower]
    return sorted(set(found))


def extract_keywords(text: str) -> list:
    text_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = text_clean.split()

    keywords = [w for w in words if len(w) > 3 and w not in STOPWORDS]

    word_counts = Counter(keywords)
    top_keywords = [word for word, count in word_counts.most_common(30)]

    return top_keywords


def parse_job_description(text: str) -> dict:
    return {
        "required_skills": extract_required_skills(text),
        "experience_level": extract_experience_level(text),
        "qualifications": extract_qualifications(text),
        "keywords": extract_keywords(text)
    }


def derive_job_title(title: str | None, content: str | None) -> str:
    """Last-resort guess when neither a typed title nor an AI-extracted one (see
    job_description_ai.parse_job_description_ai) is available. Only trusts the first line of
    the pasted content when it actually looks like a title — short, and not a full sentence —
    since job postings often open with a company blurb paragraph instead ("Gamegos is an
    accomplished game company that has been developing..."), which is prose, not a title."""
    if title:
        return title
    if content:
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
        if first_line and len(first_line) <= 60 and not first_line.endswith((".", "!", "?")):
            return first_line
    return "Untitled job description"