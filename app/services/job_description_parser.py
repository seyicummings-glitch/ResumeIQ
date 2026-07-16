import re


COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "react", "angular", "vue",
    "fastapi", "django", "flask", "node", "express", "sql", "postgresql",
    "mysql", "mongodb", "docker", "kubernetes", "aws", "azure", "gcp",
    "git", "html", "css", "rest api", "graphql", "machine learning",
    "data analysis", "c++", "c#", "go", "rust", "swift", "kotlin",
    "tensorflow", "pytorch", "linux", "agile", "scrum", "ci/cd"
]

EXPERIENCE_PATTERN = re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience", re.IGNORECASE)

QUALIFICATION_KEYWORDS = [
    "bachelor", "master", "phd", "degree", "certification", "certified",
    "diploma", "b.sc", "m.sc", "b.tech", "m.tech"
]


def extract_required_skills(text: str) -> list:
    text_lower = text.lower()
    found_skills = [skill for skill in COMMON_SKILLS if skill in text_lower]
    return sorted(set(found_skills))


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

    stopwords = {
        "the", "and", "for", "with", "you", "our", "are", "will", "have",
        "this", "that", "your", "from", "who", "what", "role", "job",
        "we", "a", "an", "to", "of", "in", "on", "as", "is", "be", "at"
    }

    keywords = [w for w in words if len(w) > 3 and w not in stopwords]

    from collections import Counter
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