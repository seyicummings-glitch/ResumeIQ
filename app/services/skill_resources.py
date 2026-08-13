"""Resolves real, clickable learning-resource links for a roadmap topic's
skill/title, as rich video/course cards rather than plain text links.

A YouTube *search* URL is never returned — clicking "Start Learning" must
always open one specific, real video, never a results page. Three-tier
lookup, most-specific first:

  1. Admin-curated SkillResource row (app/models/skill_resource_models.py) —
     whatever the admin filled in, with a thumbnail auto-derived from the
     YouTube URL even if they didn't type a title/channel/duration.
  2. Built-in curated table below — real, verified YouTube videos (checked
     via web search, not guessed — a hallucinated video ID would be worse
     than no video at all) paired with a named course, matched against the
     specific missing skill's title.
  3. Profession "closest match" fallback — when no entry above matches the
     exact skill, but the caller tells us which profession category the
     roadmap was built for (e.g. "marketing", "accounting"), we hand back
     that profession's representative curated entry (marked
     "exact_match": False so the UI can be honest that it's the closest
     relevant resource, not a precise match) instead of ever generating a
     search link. Every profession category — including "general" — has a
     representative entry, so this tier always succeeds.

Used by app/routes/roadmap.py at serialization time, so it applies uniformly
to both the AI-generated and rule-based roadmap paths without either needing
to know about it.
"""
import re

from sqlalchemy.orm import Session

from app.models.skill_resource_models import SkillResource


def normalize_skill_key(skill: str) -> str:
    """Lowercases and strips to bare alphanumerics/spaces so minor formatting
    differences ("Node.js" vs "node js") still match the same curated row."""
    return re.sub(r"[^a-z0-9 ]", "", (skill or "").lower()).strip()


_YOUTUBE_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtube\.com/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def extract_youtube_video_id(url: str | None) -> str | None:
    """Supports youtube.com/watch?v=, youtu.be/, /embed/, and /shorts/ URL shapes."""
    if not url:
        return None
    match = _YOUTUBE_ID_PATTERN.search(url)
    return match.group(1) if match else None


def youtube_thumbnail_url(video_id: str | None) -> str | None:
    """YouTube's public thumbnail CDN — no API key needed, just the video ID."""
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else None


# ---------------------------------------------------------------------------
# Built-in curated videos — every entry below was verified via live web
# search (real video ID, title, channel) rather than recalled from memory,
# specifically to avoid ever linking a plausible-sounding but nonexistent or
# mismatched video. Deliberately not exhaustive: unmatched skills fall
# through to the generated-search tier instead of a guessed pick.
# ---------------------------------------------------------------------------

_CURATED_VIDEO_TABLE = [
    (re.compile(r"\breact\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=bMknfKXIFA8",
        "youtube_title": "React Course - Beginner's Tutorial for React JavaScript Library [2022]",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "10 Hours",
        "course_title": "React - The Complete Guide (Maximilian Schwarzmüller)",
        "course_url": "https://www.udemy.com/course/react-the-complete-guide-incl-redux/",
        "course_provider": "Udemy",
        "docs_url": "https://react.dev",
    }),
    (re.compile(r"\bgit\b|\bgithub\b|version control", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=mAFoROnOfHs",
        "youtube_title": "Git & GitHub Crash Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "1.5 Hours",
        "course_title": "Git Complete: The Definitive, Step-by-Step Guide",
        "course_url": "https://www.udemy.com/course/git-complete/",
        "course_provider": "Udemy",
        "docs_url": "https://git-scm.com/doc",
    }),
    (re.compile(r"\bdocker\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=3c-iBn73dDE",
        "youtube_title": "Docker Tutorial for Beginners [FULL COURSE in 3 Hours]",
        "youtube_channel": "TechWorld with Nana",
        "youtube_duration": "3 Hours",
        "course_title": "Docker Mastery by Bret Fisher",
        "course_url": "https://www.udemy.com/course/docker-mastery/",
        "course_provider": "Udemy",
        "docs_url": "https://docs.docker.com",
    }),
    (re.compile(r"\bpython\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
        "youtube_title": "Learn Python - Full Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "4.5 Hours",
        "course_title": "100 Days of Code: The Complete Python Pro Bootcamp",
        "course_url": "https://www.udemy.com/course/100-days-of-code/",
        "course_provider": "Udemy",
        "docs_url": "https://docs.python.org",
    }),
    (re.compile(r"\bsql\b|\bpostgres(ql)?\b|\bmysql\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=HXV3zeQKqGY",
        "youtube_title": "SQL Tutorial - Full Database Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "4 Hours",
        "course_title": "The Complete SQL Bootcamp",
        "course_url": "https://www.udemy.com/course/the-complete-sql-bootcamp/",
        "course_provider": "Udemy",
        "docs_url": "https://www.postgresql.org/docs/",
    }),
    (re.compile(r"\bexcel\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=Vl0H-qTclOg",
        "youtube_title": "Microsoft Excel Tutorial for Beginners - Full Course",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "2.5 Hours",
        "course_title": "Excel Skills for Business Specialization",
        "course_url": "https://www.coursera.org/specializations/excel",
        "course_provider": "Coursera",
        "docs_url": "https://support.microsoft.com/excel",
    }),
    (re.compile(r"\bseo\b|search engine optimization", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=kaWZXRts9ls",
        "youtube_title": "SEO Full Course | SEO Tutorial For Beginners | Complete SEO Training",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "SEO for Beginners: A Basic Search Engine Optimization Tutorial",
        "course_url": "https://www.udemy.com/course/seo-training/",
        "course_provider": "Udemy",
        "docs_url": "https://developers.google.com/search/docs",
    }),
    (re.compile(r"\btableau\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=TPMlZxRRaBQ",
        "youtube_title": "Tableau for Data Science and Data Visualization - Crash Course",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "0.5 Hours",
        "course_title": "Tableau 2022 A-Z: Hands-On Tableau Training For Data Science",
        "course_url": "https://www.udemy.com/course/tableau10/",
        "course_provider": "Udemy",
        "docs_url": "https://help.tableau.com",
    }),

    # --- Business & Finance ---------------------------------------------
    (re.compile(r"powerpoint|\bppt\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=l5Ij7nUy9UQ",
        "youtube_title": "PowerPoint Tutorial for Beginners",
        "youtube_channel": "Kevin Stratvert",
        "youtube_duration": None,
        "course_title": "Microsoft PowerPoint - Complete PowerPoint Course For Beginners",
        "course_url": "https://www.udemy.com/course/microsoft-powerpoint-complete-powerpoint-course-for-beginners/",
        "course_provider": "Udemy",
        "docs_url": "https://support.microsoft.com/en-us/powerpoint",
    }),
    (re.compile(r"\bbudget", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=-vVp185Sq24",
        "youtube_title": "Budgeting For Beginners | How To Create A Budget From Scratch",
        "youtube_channel": "Austin Williams",
        "youtube_duration": None,
        "course_title": "Master Your Budget: A Comprehensive 30-Day Budgeting Course",
        "course_url": "https://www.udemy.com/course/master-your-budget-a-comprehensive-30-day-budgeting-course/",
        "course_provider": "Udemy",
        "docs_url": None,
    }),
    (re.compile(r"\breporting\b|dashboard", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=OiMMxHpR_WY",
        "youtube_title": "Excel Dashboard Design | How To Build Excel Dashboard | Excel Tutorial For Beginners",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Dynamic Dashboards: Report and Visualize Data",
        "course_url": "https://www.coursera.org/learn/dynamic-dashboards-report-and-visualize-data",
        "course_provider": "Coursera",
        "docs_url": "https://support.microsoft.com/en-us/excel",
    }),
    (re.compile(r"stakeholder", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=EDLHTOnwA4Y",
        "youtube_title": "Mastering Stakeholder Management: A Beginner's Guide",
        "youtube_channel": "CodeLucky",
        "youtube_duration": None,
        "course_title": "Google Stakeholder Management",
        "course_url": "https://www.coursera.org/specializations/google-stakeholder-management",
        "course_provider": "Coursera",
        "docs_url": None,
    }),
    (re.compile(r"project management", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=iNJYpHMjvSY",
        "youtube_title": "Project Management Full Course | Project Management Tutorial | PMP Course",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Google Project Management",
        "course_url": "https://www.coursera.org/professional-certificates/google-project-management",
        "course_provider": "Coursera",
        "docs_url": "https://www.pmi.org/",
    }),
    (re.compile(r"\bdata analy", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=wDHcQFMN9mc",
        "youtube_title": "Business Analysis Full Course | Business Analytics Tutorial For Beginners",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Google Data Analytics",
        "course_url": "https://www.coursera.org/professional-certificates/google-data-analytics",
        "course_provider": "Coursera",
        "docs_url": None,
    }),
    (re.compile(r"bookkeep|accounting basics|\breconcil", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=a3GqDaIw8pA",
        "youtube_title": "BOOKKEEPING BASICS: 7 Steps to Get You Started",
        "youtube_channel": "Accounting Stuff",
        "youtube_duration": None,
        "course_title": "Bookkeeping Basics",
        "course_url": "https://www.coursera.org/learn/bookkeeping-basics",
        "course_provider": "Coursera (Intuit)",
        "docs_url": None,
    }),
    (re.compile(r"financial model", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=Rf2QhfF9LgA",
        "youtube_title": "Financial Modeling Full Course for Beginners [With Practical Case Study]",
        "youtube_channel": "QuintEdge",
        "youtube_duration": None,
        "course_title": "Financial & Valuation Modeling Certification",
        "course_url": "https://www.wallstreetprep.com/self-study-programs/premium-package/",
        "course_provider": "Wall Street Prep",
        "docs_url": None,
    }),
    (re.compile(r"\bkpi\b|performance (management|tracking)", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=v8cLipDQS_w",
        "youtube_title": "Introduction To KPI Analysis and Techniques Certification Training",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Mastering Key Performance Indicators (KPIs)",
        "course_url": "https://www.udemy.com/course/mastering-key-performance-indicators-kpis/",
        "course_provider": "Udemy",
        "docs_url": "https://www.kpi.org/",
    }),
    (re.compile(r"business writing|documentation management|\bdocumentation\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=NN9OT-mNVIc",
        "youtube_title": "Better Business Writing (Tutorial)",
        "youtube_channel": "Excel with Business",
        "youtube_duration": None,
        "course_title": "Writing for Business",
        "course_url": "https://www.coursera.org/learn/writing-for-business",
        "course_provider": "Coursera",
        "docs_url": None,
    }),

    # --- Marketing ---------------------------------------------------------
    (re.compile(r"digital marketing|\bbrand(ing)?\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=I7zvPoQRVYA",
        "youtube_title": "Digital Marketing Full Course For Beginners | Digital Marketing Complete Course",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Digital Marketing Certification Course",
        "course_url": "https://academy.hubspot.com/courses/digital-marketing",
        "course_provider": "HubSpot Academy",
        "docs_url": None,
    }),
    (re.compile(r"content marketing", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=osVm6UrwEYc",
        "youtube_title": "Content Marketing Full Course | Content Marketing Tutorial For Beginners",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Content Marketing Certification Course",
        "course_url": "https://academy.hubspot.com/courses/content-marketing",
        "course_provider": "HubSpot Academy",
        "docs_url": None,
    }),
    (re.compile(r"email marketing", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=W9fQP4TqHfk",
        "youtube_title": "Email Marketing Full Course | Email Marketing Tutorial For Beginners",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Email Marketing Certification",
        "course_url": "https://academy.hubspot.com/courses/email-marketing-certification-en",
        "course_provider": "HubSpot Academy",
        "docs_url": None,
    }),
    (re.compile(r"social media marketing", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=oG6HXDpsu9o",
        "youtube_title": "Social Media Marketing Full Course | Social Media Marketing Tutorial For Beginners",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Social Media Marketing Certification Course",
        "course_url": "https://academy.hubspot.com/courses/social-media",
        "course_provider": "HubSpot Academy",
        "docs_url": None,
    }),
    (re.compile(r"copywriting", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=tC6bom34his",
        "youtube_title": "The Copywriting Megacourse | The Only Course You Need to Launch Your Career",
        "youtube_channel": "Copy That!",
        "youtube_duration": None,
        "course_title": "Copywriting Secrets - How to Write Copy That Sells",
        "course_url": "https://www.udemy.com/course/copywriting-secrets/",
        "course_provider": "Udemy",
        "docs_url": None,
    }),

    # --- Software engineering (additional) ----------------------------------
    (re.compile(r"javascript", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=PkZNo7MFNFg",
        "youtube_title": "Learn JavaScript - Full Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "3.5 Hours",
        "course_title": "The Complete JavaScript Course: From Zero to Expert!",
        "course_url": "https://www.udemy.com/course/the-complete-javascript-course/",
        "course_provider": "Udemy",
        "docs_url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    }),
    (re.compile(r"\bhtml\b|\bcss\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=a_iQb1lnAEQ",
        "youtube_title": "Learn HTML & CSS – Full Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": None,
        "course_title": "Responsive Web Design",
        "course_url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/",
        "course_provider": "freeCodeCamp",
        "docs_url": "https://developer.mozilla.org/en-US/docs/Web/HTML",
    }),
    (re.compile(r"\bjava\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=A74TOX803D0",
        "youtube_title": "Java Programming for Beginners – Full Course",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "4 Hours",
        "course_title": "Java Programming Masterclass",
        "course_url": "https://www.udemy.com/course/java-the-complete-java-developer-course/",
        "course_provider": "Udemy",
        "docs_url": "https://docs.oracle.com/en/java/",
    }),
    (re.compile(r"machine learning", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=i_LwzRVP7bg",
        "youtube_title": "Machine Learning for Everybody – Full Course",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": None,
        "course_title": "Machine Learning Specialization",
        "course_url": "https://www.coursera.org/specializations/machine-learning-introduction",
        "course_provider": "Coursera (Andrew Ng / DeepLearning.AI)",
        "docs_url": "https://scikit-learn.org/stable/",
    }),
    (re.compile(r"\baws\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=NhDYbskXRgc",
        "youtube_title": "AWS Certified Cloud Practitioner Certification Course (CLF-C02)",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": None,
        "course_title": "AWS Certified Cloud Practitioner exam prep",
        "course_url": "https://skillbuilder.aws/exam-prep/cloud-practitioner",
        "course_provider": "AWS Skill Builder",
        "docs_url": "https://docs.aws.amazon.com/",
    }),
    (re.compile(r"typescript", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=SpwzRDUQ1GI",
        "youtube_title": "Learn TypeScript - Full Course for Beginners",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": None,
        "course_title": "Understanding TypeScript",
        "course_url": "https://www.udemy.com/course/understanding-typescript/",
        "course_provider": "Udemy",
        "docs_url": "https://www.typescriptlang.org/docs/",
    }),
    (re.compile(r"\bagile\b|\bscrum\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=TIwa3V6GNdM",
        "youtube_title": "Agile and SCRUM Full Course | Agile SCRUM Tutorial | Agile SCRUM Training",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Professional Scrum Master (PSM) certification",
        "course_url": "https://www.scrum.org/professional-scrum-certifications",
        "course_provider": "Scrum.org",
        "docs_url": "https://scrumguides.org/",
    }),
    (re.compile(r"\bux\b|user experience|ui/?ux", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=x5OSOCMrOYY",
        "youtube_title": "UI/UX Design Full Course | UI UX Design Tutorial for Beginners",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Google UX Design",
        "course_url": "https://www.coursera.org/professional-certificates/google-ux-design",
        "course_provider": "Coursera",
        "docs_url": None,
    }),
    (re.compile(r"\bfigma\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=mT_Jjn8RJdo",
        "youtube_title": "Learn Figma in 6 Hours – Full Course",
        "youtube_channel": "freeCodeCamp.org",
        "youtube_duration": "6 Hours",
        "course_title": "Figma UI/UX Design: Web and App Design with Projects",
        "course_url": "https://www.udemy.com/course/learn-figma-web-design/",
        "course_provider": "Udemy",
        "docs_url": "https://help.figma.com/",
    }),

    # --- Other professions ---------------------------------------------------
    (re.compile(r"salesforce|\bcrm\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=a5oxfjdoJOg",
        "youtube_title": "Salesforce CRM FULL Tutorial For Beginners | Complete Training Masterclass",
        "youtube_channel": "Drew Brockbank | Brockbank Consulting",
        "youtube_duration": None,
        "course_title": "Admin Beginner Trail",
        "course_url": "https://trailhead.salesforce.com/content/learn/trails/force_com_admin_beginner",
        "course_provider": "Salesforce Trailhead",
        "docs_url": "https://trailhead.salesforce.com/",
    }),
    (re.compile(r"\bsales\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=2fweqpyCqjg",
        "youtube_title": "Full Sales Management Course (With Detailed Case Studies)",
        "youtube_channel": "Marketing91",
        "youtube_duration": None,
        "course_title": "Sales Fundamentals: Essential Sales Techniques for Beginners",
        "course_url": "https://www.udemy.com/course/your-first-time-in-sales/",
        "course_provider": "Udemy",
        "docs_url": None,
    }),
    (re.compile(r"customer service", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=SsNfAOTZNZY",
        "youtube_title": "Customer Service Training Course! (Customer Service Skills)",
        "youtube_channel": "CareerVidz",
        "youtube_duration": None,
        "course_title": "Customer Service",
        "course_url": "https://www.goskills.com/course/customer-service",
        "course_provider": "GoSkills",
        "docs_url": None,
    }),
    (re.compile(r"medical terminology", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=lxQFHKGvGJE",
        "youtube_title": "Medical Terminology | Full Course",
        "youtube_channel": "MedicoMedics",
        "youtube_duration": None,
        "course_title": "Medical Terminology",
        "course_url": "https://www.coursera.org/learn/medical-terminology",
        "course_provider": "Coursera (University of Pittsburgh)",
        "docs_url": None,
    }),
    (re.compile(r"public speaking", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=xVgALqSLRmw",
        "youtube_title": "Complete Public Speaking Course",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Dynamic Public Speaking",
        "course_url": "https://www.coursera.org/specializations/public-speaking",
        "course_provider": "Coursera (University of Washington)",
        "docs_url": None,
    }),
    (re.compile(r"time management", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=I0Dp1D9MLSU",
        "youtube_title": "Time Management & Productivity: Full Course",
        "youtube_channel": "Tales Augusto",
        "youtube_duration": None,
        "course_title": "Time Management Fundamentals",
        "course_url": "https://www.linkedin.com/learning/time-management-fundamentals-14548057",
        "course_provider": "LinkedIn Learning",
        "docs_url": None,
    }),
    (re.compile(r"\bleadership\b", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=KI6HlNPZGbM",
        "youtube_title": "Free Leadership Course | Leadership Crash Course | Leadership Certification",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Leadership for Absolute Beginners",
        "course_url": "https://www.udemy.com/course/leadership-for-absolute-beginners/",
        "course_provider": "Udemy",
        "docs_url": None,
    }),
    (re.compile(r"negotiation", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=TpRTCmK2QMA",
        "youtube_title": "Negotiation Skills Training | Full Course | Free Business Skills Training",
        "youtube_channel": "Sprintzeal",
        "youtube_duration": None,
        "course_title": "Successful Negotiation: Essential Strategies and Skills",
        "course_url": "https://www.coursera.org/learn/negotiation-skills",
        "course_provider": "Coursera (University of Michigan)",
        "docs_url": None,
    }),
    (re.compile(r"power ?bi", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=cyWVzAQF9YU",
        "youtube_title": "Power BI Complete Course - Beginner to Expert in 20 Hours",
        "youtube_channel": "Amit Chandak",
        "youtube_duration": "20 Hours",
        "course_title": "Microsoft Power BI Data Analyst",
        "course_url": "https://learn.microsoft.com/en-us/training/powerplatform/power-bi",
        "course_provider": "Microsoft Learn",
        "docs_url": "https://learn.microsoft.com/en-us/power-bi/",
    }),
    (re.compile(r"supply chain", re.IGNORECASE), {
        "youtube_url": "https://www.youtube.com/watch?v=m1WMfclNAZM",
        "youtube_title": "Supply Chain Management Full Course | Digital Supply Chain Management Tutorial",
        "youtube_channel": "Simplilearn",
        "youtube_duration": None,
        "course_title": "Supply Chain Management",
        "course_url": "https://www.coursera.org/specializations/supply-chain-management",
        "course_provider": "Coursera (Rutgers University)",
        "docs_url": None,
    }),
]


def _curated_video_match(normalized_title: str) -> dict | None:
    for pattern, entry in _CURATED_VIDEO_TABLE:
        if pattern.search(normalized_title):
            return entry
    return None


def _find_best_match(normalized_title: str, resources: list[SkillResource]) -> SkillResource | None:
    if not normalized_title:
        return None
    for resource in resources:
        if resource.skill_key == normalized_title:
            return resource
    for resource in resources:
        if resource.skill_key and resource.skill_key in normalized_title:
            return resource
    return None


def _with_thumbnail(payload: dict, youtube_url: str | None) -> dict:
    video_id = extract_youtube_video_id(youtube_url)
    return {**payload, "youtubeVideoId": video_id, "youtubeThumbnailUrl": youtube_thumbnail_url(video_id)}


# ---------------------------------------------------------------------------
# Profession "closest match" fallback. Every category detect_profession_category()
# (see app/services/learning_roadmap.py) can return maps to a search string that's
# guaranteed to match an entry in _CURATED_VIDEO_TABLE above (locked in by
# test_skill_resources.py) — so a topic whose exact skill has no curated match
# still gets a real, specific, relevant video for the user's field instead of
# ever falling through to a generated search link.
# ---------------------------------------------------------------------------

_PROFESSION_FALLBACK_QUERY = {
    "software_engineering": "python",
    "marketing": "digital marketing",
    "accounting": "bookkeeping",
    "business_administration": "project management",
    "data_science": "data analysis",
    "healthcare": "medical terminology",
    "human_resources": "leadership",
    "legal": "negotiation",
    "design": "ux design",
    "sales": "sales",
    "education": "public speaking",
    "customer_service": "customer service",
    "general": "time management",
}


def _profession_fallback(profession_category: str | None) -> dict:
    query = _PROFESSION_FALLBACK_QUERY.get(profession_category or "general", _PROFESSION_FALLBACK_QUERY["general"])
    match = _curated_video_match(query)
    # Every value above is guaranteed by construction (and locked in by tests) to match
    # something in _CURATED_VIDEO_TABLE — the "general" re-lookup below is a defensive
    # fallback only, in case that guarantee is ever broken by a future edit, so this
    # function structurally cannot return None and force a caller back to a search link.
    return match or _curated_video_match(_PROFESSION_FALLBACK_QUERY["general"])


def get_resource_links(skill: str, all_resources: list[SkillResource], profession_category: str | None = None) -> dict:
    """`all_resources` is the full SkillResource table, fetched once by the
    caller (see app/routes/roadmap.py) rather than re-queried per topic —
    a roadmap has 15-20 topics, and this table is small enough to hold in
    memory for the duration of one request. `profession_category` is the
    roadmap's detected profession category key (e.g. "marketing"), used only
    as the closest-match fallback when the exact skill isn't curated —
    never returns a YouTube search URL, however unmatched the skill is."""
    normalized = normalize_skill_key(skill)

    admin_match = _find_best_match(normalized, all_resources)
    if admin_match is not None:
        return _with_thumbnail({
            "youtubeUrl": admin_match.youtube_url or None,
            "youtubeTitle": admin_match.youtube_title or None,
            "youtubeChannel": admin_match.youtube_channel or None,
            "youtubeDuration": admin_match.youtube_duration or None,
            "courseUrl": admin_match.course_url or None,
            "courseTitle": admin_match.course_title or None,
            "courseProvider": admin_match.course_provider or None,
            "docsUrl": admin_match.docs_url or None,
            "curated": True,
            "exactMatch": True,
        }, admin_match.youtube_url)

    curated = _curated_video_match(normalized)
    if curated is not None:
        return _with_thumbnail({
            "youtubeUrl": curated["youtube_url"],
            "youtubeTitle": curated["youtube_title"],
            "youtubeChannel": curated["youtube_channel"],
            "youtubeDuration": curated["youtube_duration"],
            "courseUrl": curated["course_url"],
            "courseTitle": curated["course_title"],
            "courseProvider": curated["course_provider"],
            "docsUrl": curated["docs_url"],
            "curated": True,
            "exactMatch": True,
        }, curated["youtube_url"])

    fallback = _profession_fallback(profession_category)
    return _with_thumbnail({
        "youtubeUrl": fallback["youtube_url"],
        "youtubeTitle": fallback["youtube_title"],
        "youtubeChannel": fallback["youtube_channel"],
        "youtubeDuration": fallback["youtube_duration"],
        "courseUrl": fallback["course_url"],
        "courseTitle": fallback["course_title"],
        "courseProvider": fallback["course_provider"],
        "docsUrl": fallback["docs_url"],
        "curated": True,
        "exactMatch": False,
    }, fallback["youtube_url"])


def fetch_all_resources(db: Session) -> list[SkillResource]:
    return db.query(SkillResource).all()
