from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def calculate_match_score(resume_text: str, job_description: str) -> dict:
    resume_clean = clean_text(resume_text)
    jd_clean = clean_text(job_description)

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([resume_clean, jd_clean])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    match_percentage = round(similarity * 100, 2)

    jd_words = set(jd_clean.split())
    resume_words = set(resume_clean.split())

    common_stopwords = {"and", "the", "for", "with", "you", "our", "are", "will", "have", "this", "that"}
    jd_keywords = {w for w in jd_words if len(w) > 3 and w not in common_stopwords}

    matched_keywords = list(jd_keywords & resume_words)
    missing_keywords = list(jd_keywords - resume_words)

    return {
        "match_percentage": match_percentage,
        "matched_keywords": sorted(matched_keywords)[:30],
        "missing_keywords": sorted(missing_keywords)[:30],
        "matched_count": len(matched_keywords),
        "missing_count": len(missing_keywords)
    }