from app.services.job_description_parser import parse_job_description
from app.services.matching_engine import calculate_overall_match


def rank_jobs_for_resume(resume_text: str, resume_skills: list, job_descriptions: list) -> list:
    """job_descriptions: list of {"id": int, "title": str|None, "content": str}."""
    results = []
    for jd in job_descriptions:
        parsed = parse_job_description(jd["content"])
        match = calculate_overall_match(
            resume_text=resume_text,
            resume_skills=resume_skills,
            jd_required_skills=parsed["required_skills"],
            jd_experience_level=parsed["experience_level"],
            jd_qualifications=parsed["qualifications"]
        )
        results.append({
            "job_description_id": jd["id"],
            "title": jd.get("title"),
            "overall_match_score": match["overall_match_score"],
            "skill_match": match["skill_match"],
            "experience_match": match["experience_match"],
            "qualification_match": match["qualification_match"]
        })

    results.sort(key=lambda r: r["overall_match_score"], reverse=True)
    return results
