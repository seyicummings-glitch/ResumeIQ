import time
from app.services.resume_parser import extract_resume_text
from app.services.resume_structurer import structure_resume
from app.services.job_description_parser import parse_job_description
from app.services.matching_engine import calculate_overall_match
from app.services.ats_scorer import calculate_ats_score

SAMPLE_RESUME = """
Jane Doe
Email: jane.doe@example.com
Phone: 555-123-4567
LinkedIn: linkedin.com/in/janedoe

Summary
Backend engineer with 6 years of experience building APIs and data pipelines.

Skills
Python, FastAPI, PostgreSQL, Docker, AWS, React, SQL, Git, Linux, Kubernetes

Experience
Senior Backend Engineer at TechCorp, 2020-2026
Built and maintained REST APIs serving millions of requests per day using FastAPI and PostgreSQL.
Deployed services on AWS using Docker and Kubernetes.
Led migration of legacy monolith to microservices architecture.

Backend Developer at StartupCo, 2018-2020
Developed internal tools using Python and SQL.
Collaborated with frontend team on React-based dashboards.

Education
B.S. Computer Science, State University, 2018

Certifications
AWS Certified Solutions Architect

Projects
ResumeIQ - AI-powered resume analysis platform built with FastAPI and PostgreSQL.
"""

SAMPLE_JD = """
Senior Backend Engineer

We are looking for a Senior Backend Engineer with 5+ years of experience in Python,
FastAPI, PostgreSQL, Docker, and AWS. Experience with Kubernetes and microservices
architecture is a strong plus. Bachelor's degree in Computer Science or related field required.
"""


def test_full_analysis_completes_within_10_seconds():
    resume_bytes = SAMPLE_RESUME.encode("utf-8")
    start = time.perf_counter()

    text = extract_resume_text("resume.txt", resume_bytes)
    structured = structure_resume(text)
    jd_parsed = parse_job_description(SAMPLE_JD)
    calculate_overall_match(
        resume_text=text,
        resume_skills=structured["skills"],
        jd_required_skills=jd_parsed["required_skills"],
        jd_experience_level=jd_parsed["experience_level"],
        jd_qualifications=jd_parsed["qualifications"]
    )
    calculate_ats_score("resume.txt", text, structured)

    elapsed = time.perf_counter() - start
    assert elapsed < 10.0, f"Full analysis took {elapsed:.2f}s, expected under 10s"
