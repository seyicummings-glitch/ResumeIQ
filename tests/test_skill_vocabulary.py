"""Locks in that SKILL_VOCABULARY actually covers non-technical professions,
not just software engineering — the root cause of the Learning Roadmap (and
resume/JD matching generally) defaulting to tech-flavored results for
marketing/accounting/business/healthcare candidates was this vocabulary being
almost entirely technical, which pushed extract_required_skills() into its
noisy word-frequency fallback for those fields."""
from app.services.skill_vocabulary import SKILL_VOCABULARY
from app.services.job_description_parser import extract_required_skills


def test_skill_vocabulary_has_no_duplicate_entries():
    lowered = [s.lower() for s in SKILL_VOCABULARY]
    assert len(lowered) == len(set(lowered))


def test_skill_vocabulary_covers_marketing():
    assert "SEO" in SKILL_VOCABULARY
    assert "Content Marketing" in SKILL_VOCABULARY
    assert "Google Analytics" in SKILL_VOCABULARY


def test_skill_vocabulary_covers_accounting():
    assert "GAAP" in SKILL_VOCABULARY
    assert "Accounts Payable" in SKILL_VOCABULARY
    assert "QuickBooks" in SKILL_VOCABULARY


def test_skill_vocabulary_covers_business_administration():
    assert "Strategic Planning" in SKILL_VOCABULARY
    assert "Stakeholder Management" in SKILL_VOCABULARY
    assert "Supply Chain Management" in SKILL_VOCABULARY


def test_skill_vocabulary_covers_healthcare():
    assert "Patient Care" in SKILL_VOCABULARY
    assert "HIPAA Compliance" in SKILL_VOCABULARY
    assert "Medical Coding" in SKILL_VOCABULARY


def test_skill_vocabulary_covers_human_resources_and_legal():
    assert "Talent Acquisition" in SKILL_VOCABULARY
    assert "Litigation" in SKILL_VOCABULARY
    assert "Contract Drafting" in SKILL_VOCABULARY


def test_extract_required_skills_finds_real_skills_in_a_marketing_jd_without_noise_fallback():
    text = (
        "We're looking for a Marketing Coordinator to own our SEO strategy, run Google Analytics "
        "reporting, and manage content marketing and social media marketing campaigns."
    )
    skills = extract_required_skills(text)
    assert "seo" in skills
    assert "google analytics" in skills
    assert "content marketing" in skills
    assert "social media marketing" in skills


def test_extract_required_skills_finds_real_skills_in_an_accounting_jd_without_noise_fallback():
    text = (
        "Staff Accountant responsible for accounts payable, accounts receivable, bank reconciliation, "
        "and monthly financial reporting in accordance with GAAP. QuickBooks experience required."
    )
    skills = extract_required_skills(text)
    assert "accounts payable" in skills
    assert "accounts receivable" in skills
    assert "gaap" in skills
    assert "quickbooks" in skills


def test_extract_required_skills_finds_real_skills_in_a_healthcare_jd_without_noise_fallback():
    text = (
        "Registered Nurse needed for patient care, EHR documentation, and HIPAA compliance in a "
        "fast-paced clinical environment. CPR certification required."
    )
    skills = extract_required_skills(text)
    assert "patient care" in skills
    assert "ehr" in skills
    assert "hipaa compliance" in skills
