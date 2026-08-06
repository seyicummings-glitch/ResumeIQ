"""
Rule-based resume-to-job-description matching engine.

No machine learning or AI models are used here — every score below is
computed from deterministic string/set operations over parsed resume and
job description data. The final score is a fixed weighted sum:

    overall_match_score = skill_score * 0.5
                         + experience_score * 0.3
                         + qualification_score * 0.2

Required skills are weighted highest since they're the most direct signal
of fit, experience next, and qualifications (degrees/certs) last since
they're the weakest predictor of job performance for most roles.

When GitHub language data is supplied as a secondary signal, the weights
shift to make room for it (still summing to 100, still rule-based):

    overall_match_score = skill_score * 0.45
                         + experience_score * 0.25
                         + qualification_score * 0.15
                         + github_bonus_score * 0.15
"""
import re


def _explain_skill_match(skill_score: float, matched: list, missing: list) -> str:
    total = len(matched) + len(missing)
    if total == 0:
        return (
            "No specific required skills could be identified from the job description, so this score isn't "
            "a real reflection of your resume — paste a more detailed job description with clearly named "
            "skills or technologies to get an accurate skill match."
        )
    if not missing:
        return f"You matched all {total} skill{'s' if total != 1 else ''} the job description asks for: {', '.join(matched)}."
    if not matched:
        return (
            f"None of the {total} skill{'s' if total != 1 else ''} the job asks for were found on your resume: "
            f"{', '.join(missing)}. Add whichever of these you genuinely have experience with."
        )
    return (
        f"You matched {len(matched)} of {total} skills the job asks for ({', '.join(matched)}). "
        f"Missing: {', '.join(missing)} — add these to your resume if you genuinely have relevant "
        f"experience with them to raise this score."
    )


def calculate_skill_match(resume_skills: list, jd_required_skills: list) -> dict:
    """Score skill overlap as the fraction of JD-required skills present in the resume (set intersection)."""
    resume_skills_lower = set(s.lower() for s in resume_skills)
    jd_skills_lower = set(s.lower() for s in jd_required_skills)

    matched = list(resume_skills_lower & jd_skills_lower)
    missing = list(jd_skills_lower - resume_skills_lower)

    if len(jd_skills_lower) == 0:
        skill_score = 0
    else:
        skill_score = round((len(matched) / len(jd_skills_lower)) * 100, 2)

    matched_sorted = sorted(matched)
    missing_sorted = sorted(missing)

    return {
        "skill_score": skill_score,
        "matched_skills": matched_sorted,
        "missing_skills": missing_sorted,
        "explanation": _explain_skill_match(skill_score, matched_sorted, missing_sorted),
    }


def calculate_experience_match(resume_text: str, jd_experience_level: str) -> dict:
    """Score experience fit by regex-extracting a required year count from the JD and the candidate's max stated years."""
    if jd_experience_level == "Not specified":
        return {
            "experience_score": 100,
            "note": "No specific experience requirement",
            "explanation": "The job description doesn't state a specific years-of-experience requirement, so this defaults to a full score.",
        }

    required_years_match = re.search(r"(\d+)", jd_experience_level)
    if not required_years_match:
        return {
            "experience_score": 100,
            "note": "Could not determine requirement",
            "explanation": "The job description's experience requirement couldn't be parsed into a specific number of years, so this defaults to a full score.",
        }

    required_years = int(required_years_match.group(1))

    resume_years_matches = re.findall(r"(\d+)\s*\+?\s*(?:years?|yrs?)", resume_text, re.IGNORECASE)
    resume_years = max([int(y) for y in resume_years_matches], default=0)

    if resume_years >= required_years:
        experience_score = 100
        explanation = f"The job asks for {required_years}+ years of experience, and your resume states {resume_years} — you meet or exceed it."
    elif resume_years == 0:
        experience_score = 30
        explanation = (
            f"The job asks for {required_years}+ years of experience, but no years of experience could be found "
            "stated on your resume. Add your years of experience explicitly (e.g. \"5 years of experience\") so it's detected."
        )
    else:
        experience_score = round((resume_years / required_years) * 100, 2)
        explanation = (
            f"The job asks for {required_years}+ years of experience; your resume states {resume_years}, "
            f"which is {experience_score}% of what's required."
        )

    return {
        "experience_score": experience_score,
        "required_years": required_years,
        "candidate_years_found": resume_years,
        "explanation": explanation,
    }


def calculate_qualification_match(resume_text: str, jd_qualifications: list) -> dict:
    """Score qualification fit as the fraction of JD-required qualification keywords found via substring match in the resume."""
    if not jd_qualifications:
        return {
            "qualification_score": 100,
            "note": "No specific qualification required",
            "explanation": "The job description doesn't call out a specific qualification (degree, certification, etc.), so this defaults to a full score.",
        }

    resume_text_lower = resume_text.lower()
    matched_quals = [q for q in jd_qualifications if q in resume_text_lower]
    missing_quals = [q for q in jd_qualifications if q not in resume_text_lower]

    qualification_score = round((len(matched_quals) / len(jd_qualifications)) * 100, 2)

    if not missing_quals:
        explanation = f"Your resume shows every qualification the job asks for: {', '.join(matched_quals)}."
    elif not matched_quals:
        explanation = (
            f"None of the qualifications the job asks for were found on your resume: {', '.join(missing_quals)}. "
            "Add whichever of these you genuinely hold."
        )
    else:
        explanation = (
            f"Your resume shows {len(matched_quals)} of {len(jd_qualifications)} qualifications asked for "
            f"({', '.join(matched_quals)}). Missing: {', '.join(missing_quals)}."
        )

    return {
        "qualification_score": qualification_score,
        "matched_qualifications": matched_quals,
        "missing_qualifications": missing_quals,
        "explanation": explanation,
    }


def calculate_github_bonus(github_languages: list, jd_required_skills: list) -> dict:
    """Score overlap between a candidate's GitHub languages and JD-required skills (secondary signal, max 100)."""
    if not jd_required_skills:
        return {
            "github_bonus_score": 0,
            "matched_languages": [],
            "explanation": "No required skills were identified from the job description to compare your GitHub languages against.",
        }

    languages_lower = set(l.lower() for l in github_languages)
    required_lower = set(s.lower() for s in jd_required_skills)
    matched = sorted(languages_lower & required_lower)

    score = round((len(matched) / len(required_lower)) * 100, 2)
    explanation = (
        f"{len(matched)} of {len(required_lower)} required skills show up as languages in your public GitHub repos ({', '.join(matched)})."
        if matched
        else "None of the required skills show up as languages in your public GitHub repos — this is a secondary signal, so it doesn't heavily affect your overall score."
    )
    return {"github_bonus_score": score, "matched_languages": matched, "explanation": explanation}


def _explain_overall(overall_score: float, skill_result: dict, experience_result: dict, qualification_result: dict, weights_note: str) -> str:
    lead = f"Your overall match is {overall_score}%, a weighted blend of {weights_note}."

    improvements = []
    if skill_result["missing_skills"]:
        top_missing = skill_result["missing_skills"][:5]
        suffix = ", among others" if len(skill_result["missing_skills"]) > 5 else ""
        improvements.append(f"add {', '.join(top_missing)}{suffix} to your resume if you genuinely have that experience")
    if experience_result.get("candidate_years_found") is not None and experience_result["experience_score"] < 100:
        improvements.append("state your years of experience more explicitly so it's detected")
    if qualification_result.get("missing_qualifications"):
        improvements.append(f"add {', '.join(qualification_result['missing_qualifications'])} if you genuinely hold them")

    if not improvements:
        return f"{lead} Your resume is already well aligned with what this job description asks for."

    return f"{lead} Biggest opportunities to improve this match: {'; '.join(improvements)}."


def calculate_overall_match(
    resume_text: str,
    resume_skills: list,
    jd_required_skills: list,
    jd_experience_level: str,
    jd_qualifications: list,
    github_languages: list | None = None
) -> dict:
    """Combine skill/experience/qualification scores (and, if supplied, a GitHub bonus) into the final weighted overall match score."""
    skill_result = calculate_skill_match(resume_skills, jd_required_skills)
    experience_result = calculate_experience_match(resume_text, jd_experience_level)
    qualification_result = calculate_qualification_match(resume_text, jd_qualifications)

    if github_languages:
        github_result = calculate_github_bonus(github_languages, jd_required_skills)
        overall_score = round(
            (skill_result["skill_score"] * 0.45) +
            (experience_result["experience_score"] * 0.25) +
            (qualification_result["qualification_score"] * 0.15) +
            (github_result["github_bonus_score"] * 0.15),
            2
        )
        return {
            "overall_match_score": overall_score,
            "overall_explanation": _explain_overall(
                overall_score, skill_result, experience_result, qualification_result,
                "skills (45%), experience (25%), qualifications (15%), and GitHub language overlap (15%)",
            ),
            "skill_match": skill_result,
            "experience_match": experience_result,
            "qualification_match": qualification_result,
            "github_match": github_result
        }

    # Weighted overall score: skills matter most, then experience, then qualifications
    overall_score = round(
        (skill_result["skill_score"] * 0.5) +
        (experience_result["experience_score"] * 0.3) +
        (qualification_result["qualification_score"] * 0.2),
        2
    )

    return {
        "overall_match_score": overall_score,
        "overall_explanation": _explain_overall(
            overall_score, skill_result, experience_result, qualification_result,
            "skills (50%), experience (30%), and qualifications (20%)",
        ),
        "skill_match": skill_result,
        "experience_match": experience_result,
        "qualification_match": qualification_result
    }