import re


def analyze_keywords(resume_text: str, jd_keywords: list) -> dict:
    """Compare JD keywords against resume text: matched, missing, and per-keyword frequency."""
    resume_lower = resume_text.lower()
    matched = []
    missing = []
    frequency = {}

    for keyword in jd_keywords:
        count = len(re.findall(r"\b" + re.escape(keyword.lower()) + r"\b", resume_lower))
        frequency[keyword] = count
        if count > 0:
            matched.append(keyword)
        else:
            missing.append(keyword)

    return {
        "matched_keywords": matched,
        "missing_keywords": missing,
        "keyword_frequency": frequency
    }
