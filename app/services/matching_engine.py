import re


def calculate_skill_match(resume_skills: list, jd_required_skills: list) -> dict:
    resume_skills_lower = set(s.lower() for s in resume_skills)
    jd_skills_lower = set(s.lower() for s in jd_required_skills)

    matched = list(resume_skills_lower & jd_skills_lower)
    missing = list(jd_skills_lower - resume_skills_lower)

    if len(jd_skills_lower) == 0:
        skill_score = 0
    else:
        skill_score = round((len(matched) / len(jd_skills_lower)) * 100, 2)

    return {
        "skill_score": skill_score,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing)
    }


def calculate_experience_match(resume_text: str, jd_experience_level: str) -> dict:
    if jd_experience_level == "Not specified":
        return {"experience_score": 100, "note": "No specific experience requirement"}

    required_years_match = re.search(r"(\d+)", jd_experience_level)
    if not required_years_match:
        return {"experience_score": 100, "note": "Could not determine requirement"}

    required_years = int(required_years_match.group(1))

    resume_years_matches = re.findall(r"(\d+)\s*\+?\s*(?:years?|yrs?)", resume_text, re.IGNORECASE)
    resume_years = max([int(y) for y in resume_years_matches], default=0)

    if resume_years >= required_years:
        experience_score = 100
    elif resume_years == 0:
        experience_score = 30
    else:
        experience_score = round((resume_years / required_years) * 100, 2)

    return {
        "experience_score": experience_score,
        "required_years": required_years,
        "candidate_years_found": resume_years
    }


def calculate_qualification_match(resume_text: str, jd_qualifications: list) -> dict:
    if not jd_qualifications:
        return {"qualification_score": 100, "note": "No specific qualification required"}

    resume_text_lower = resume_text.lower()
    matched_quals = [q for q in jd_qualifications if q in resume_text_lower]

    qualification_score = round((len(matched_quals) / len(jd_qualifications)) * 100, 2)

    return {
        "qualification_score": qualification_score,
        "matched_qualifications": matched_quals
    }


def calculate_overall_match(
    resume_text: str,
    resume_skills: list,
    jd_required_skills: list,
    jd_experience_level: str,
    jd_qualifications: list
) -> dict:
    skill_result = calculate_skill_match(resume_skills, jd_required_skills)
    experience_result = calculate_experience_match(resume_text, jd_experience_level)
    qualification_result = calculate_qualification_match(resume_text, jd_qualifications)

    # Weighted overall score: skills matter most, then experience, then qualifications
    overall_score = round(
        (skill_result["skill_score"] * 0.5) +
        (experience_result["experience_score"] * 0.3) +
        (qualification_result["qualification_score"] * 0.2),
        2
    )

    return {
        "overall_match_score": overall_score,
        "skill_match": skill_result,
        "experience_match": experience_result,
        "qualification_match": qualification_result
    }