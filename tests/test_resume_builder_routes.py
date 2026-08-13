from app.models.models import User, Resume
from app.routes import resume_builder as routes


def _user(db_session, **overrides):
    fields = dict(
        email="jordan@example.com", hashed_password="x", full_name="Jordan Mitchell",
        phone="+1 (555) 123-4567", linkedin_url="linkedin.com/in/jordanmitchell", location="Austin, TX",
    )
    fields.update(overrides)
    user = User(**fields)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _resume(db_session, user, **overrides):
    fields = dict(user_id=user.id, filename="resume.pdf", raw_text="Some resume text", is_active=True)
    fields.update(overrides)
    resume = Resume(**fields)
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


# --- Contact info comes from the real profile, never the AI --------------------

def test_generate_resume_merges_real_contact_info_from_profile(db_session):
    user = _user(db_session)
    _resume(db_session, user)

    result = routes.generate_resume(db=db_session, current_user=user)

    assert result["contact"] == {
        "full_name": "Jordan Mitchell", "email": "jordan@example.com",
        "phone": "+1 (555) 123-4567", "linkedin": "linkedin.com/in/jordanmitchell", "location": "Austin, TX",
    }


def test_generate_resume_contact_handles_missing_profile_fields_gracefully(db_session):
    user = _user(db_session, phone=None, linkedin_url=None, location=None)
    _resume(db_session, user)

    result = routes.generate_resume(db=db_session, current_user=user)

    assert result["contact"]["phone"] == ""
    assert result["contact"]["linkedin"] == ""
    assert result["contact"]["location"] == ""
    assert result["contact"]["email"] == "jordan@example.com"


def test_chat_resume_merges_contact_info_into_response(db_session):
    user = _user(db_session)
    input_data = routes.ResumeBuilderChatInput(
        conversation=[{"role": "user", "content": "Help me build my resume."}],
    )
    result = routes.chat_resume(input_data, db=db_session, current_user=user)
    assert result["contact"]["full_name"] == "Jordan Mitchell"


# --- Save builds a real, structured resume --------------------------------------

def test_save_enhanced_resume_builds_formatted_raw_text_with_header_and_sections(db_session):
    user = _user(db_session)
    data = routes.SaveEnhancedResumeInput(
        title="Marketing & Sales Professional",
        summary="Results-driven marketing professional.",
        skills=["SEO", "CRM", "Negotiation"],
        experience=[routes.ExperienceItemInput(
            title="Senior Marketing Manager", company="Brightline Consumer Goods Co.",
            start_date="Mar 2022", end_date="Present",
            bullets=["Led a cross-functional team of 8.", "Grew annual recurring revenue by $1.2M."],
        )],
        education=[routes.EducationItemInput(degree="BBA, Marketing", school="University of Texas at Austin", date="May 2017")],
        certifications=["HubSpot Inbound Marketing Certification"],
    )

    result = routes.save_enhanced_resume(data, db=db_session, current_user=user)
    saved = db_session.query(Resume).filter(Resume.id == result["resume_id"]).first()

    assert saved.source == "ai_builder"
    assert "Jordan Mitchell" in saved.raw_text
    assert "Marketing & Sales Professional" in saved.raw_text
    assert "jordan@example.com" in saved.raw_text
    assert "PROFESSIONAL SUMMARY" in saved.raw_text
    assert "CORE SKILLS" in saved.raw_text
    assert "SEO • CRM • Negotiation" in saved.raw_text
    assert "PROFESSIONAL EXPERIENCE" in saved.raw_text
    assert "Senior Marketing Manager | Brightline Consumer Goods Co." in saved.raw_text
    assert "Led a cross-functional team of 8." in saved.raw_text
    assert "EDUCATION" in saved.raw_text
    assert "BBA, Marketing, University of Texas at Austin (May 2017)" in saved.raw_text
    assert "CERTIFICATIONS" in saved.raw_text
    assert "HubSpot Inbound Marketing Certification" in saved.raw_text

    assert saved.skills == "SEO, CRM, Negotiation"
    assert "University of Texas at Austin" in saved.education
    assert "HubSpot Inbound Marketing Certification" in saved.certifications


def test_save_enhanced_resume_falls_back_to_original_education_when_draft_has_none(db_session):
    user = _user(db_session)
    original = _resume(db_session, user, education="BSc Computer Science, MIT", certifications="AWS Certified")

    data = routes.SaveEnhancedResumeInput(
        resume_id=original.id, title="Engineer", summary="Summary.",
        skills=["Python"], experience=[], education=[], certifications=[],
    )
    result = routes.save_enhanced_resume(data, db=db_session, current_user=user)
    saved = db_session.query(Resume).filter(Resume.id == result["resume_id"]).first()

    assert saved.education == "BSc Computer Science, MIT"
    assert saved.certifications == "AWS Certified"


def test_save_enhanced_resume_draft_education_takes_precedence_over_original(db_session):
    user = _user(db_session)
    original = _resume(db_session, user, education="Stale old degree")

    data = routes.SaveEnhancedResumeInput(
        resume_id=original.id, title="Engineer", summary="Summary.", skills=[], experience=[],
        education=[routes.EducationItemInput(degree="MSc Data Science", school="Stanford", date="2023")],
        certifications=[],
    )
    result = routes.save_enhanced_resume(data, db=db_session, current_user=user)
    saved = db_session.query(Resume).filter(Resume.id == result["resume_id"]).first()

    assert "MSc Data Science" in saved.education
    assert "Stale old degree" not in saved.education
