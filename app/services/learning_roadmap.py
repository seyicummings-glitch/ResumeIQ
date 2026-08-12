"""
Rule-based learning roadmap builder — the no-AI fallback for
app/services/learning_roadmap_ai.py. No machine learning here: resources,
providers, and stage groupings are selected deterministically from fixed
lookup tables keyed by regex/keyword matches. Mirrors the style of
matching_engine.py: pure functions, no FastAPI/SQLAlchemy imports.

Produces {"stages": [...], "detected_profession": str, "detected_industry": str}
— the same shape the AI path returns (see learning_roadmap_ai.py's
ROADMAP_SCHEMA) so the route layer and frontend don't need to special-case
which path generated the roadmap.

Foundation and Job Ready used to be one fixed, software-engineering-specific
set of topics for every single user (Git, data structures, system design —
regardless of whether the candidate was a marketer or an accountant). They
now come from detect_profession_category()'s best guess at the candidate's
field, picked from a per-category bank — never defaulting to software
engineering just because that's what this lookup table happened to have
first. Intermediate/Advanced were already built purely from the caller's
missing_skills list, which is inherently profession-agnostic (whatever gaps
were actually identified), so those needed no change.
"""
import math
import re

STAGE_NAMES = ["Foundation", "Intermediate", "Advanced", "Job Ready"]

# Each entry: (regex pattern, [3 realistic named resources])
_RESOURCE_TABLE = [
    (re.compile(r"\bdocker\b", re.IGNORECASE), [
        "Docker Mastery by Bret Fisher (Udemy)",
        "Docker Curriculum (docker-curriculum.com) — free",
        "Docker Certified Associate (DCA) certification guide",
    ]),
    (re.compile(r"\bkubernetes\b|\bk8s\b", re.IGNORECASE), [
        "Kubernetes for the Absolute Beginners (Udemy, Mumshad Mannambeth)",
        "Kubernetes.io official documentation and tutorials — free",
        "Certified Kubernetes Application Developer (CKAD) study guide",
    ]),
    (re.compile(r"\bgraphql\b", re.IGNORECASE), [
        "GraphQL with React: The Complete Developers Guide (Udemy)",
        "How to GraphQL (howtographql.com) — free",
        "Learning GraphQL by Eve Porcello & Alex Banks (O'Reilly)",
    ]),
    (re.compile(r"\baws\b|\bcloud\b", re.IGNORECASE), [
        "AWS Certified Solutions Architect – Associate (Stephane Maarek, Udemy)",
        "AWS Skill Builder — free digital training",
        "AWS Certified Solutions Architect Associate certification",
    ]),
    (re.compile(r"\btypescript\b", re.IGNORECASE), [
        "Understanding TypeScript by Maximilian Schwarzmüller (Udemy)",
        "TypeScript Handbook (typescriptlang.org) — free",
        "Effective TypeScript by Dan Vanderkam (O'Reilly)",
    ]),
    (re.compile(r"\breact\b", re.IGNORECASE), [
        "Epic React by Kent C. Dodds",
        "React official documentation (react.dev) — free",
        "React - The Complete Guide (Maximilian Schwarzmüller, Udemy)",
    ]),
    (re.compile(r"\bpython\b", re.IGNORECASE), [
        "100 Days of Code: The Complete Python Pro Bootcamp (Udemy)",
        "Python official tutorial (docs.python.org) — free",
        "Python Institute PCEP/PCAP certification",
    ]),
    (re.compile(r"\bsql\b|\bpostgres(ql)?\b", re.IGNORECASE), [
        "The Complete SQL Bootcamp (Jose Portilla, Udemy)",
        "PostgreSQL official tutorial (postgresql.org/docs) — free",
        "SQL for Data Analysis by Cathy Tanimura (O'Reilly)",
    ]),
    (re.compile(r"machine learning|\bml\b", re.IGNORECASE), [
        "Machine Learning Specialization (Andrew Ng, Coursera)",
        "Google's Machine Learning Crash Course — free",
        "Hands-On Machine Learning with Scikit-Learn, Keras & TensorFlow (O'Reilly)",
    ]),
    (re.compile(r"\bnode(\.js)?\b", re.IGNORECASE), [
        "The Complete Node.js Developer Course (Andrew Mead, Udemy)",
        "Node.js official documentation (nodejs.org) — free",
        "Node.js Design Patterns by Mario Casciaro (Packt)",
    ]),
    (re.compile(r"\brust\b", re.IGNORECASE), [
        "Rust Programming Language: The Complete Guide (Udemy)",
        "The Rust Book (doc.rust-lang.org/book) — free",
        "Programming Rust by Jim Blandy (O'Reilly)",
    ]),
    (re.compile(r"\bgo(lang)?\b", re.IGNORECASE), [
        "Learn Go: An Introduction to Programming (Udemy, Todd McLeod)",
        "A Tour of Go (go.dev/tour) — free",
        "The Go Programming Language by Donovan & Kernighan",
    ]),
    (re.compile(r"ci/cd|\bci\b|\bcd\b|continuous integration|continuous delivery", re.IGNORECASE), [
        "CI/CD Pipelines with GitHub Actions (Udemy)",
        "GitHub Actions official documentation — free",
        "Continuous Delivery by Jez Humble & David Farley",
    ]),
    (re.compile(r"\bterraform\b", re.IGNORECASE), [
        "HashiCorp Certified: Terraform Associate Course (Udemy)",
        "Terraform official tutorials (developer.hashicorp.com) — free",
        "Terraform Associate certification",
    ]),
    (re.compile(r"\bredis\b", re.IGNORECASE), [
        "Redis: The Complete Developer's Guide (Udemy)",
        "Redis official documentation (redis.io/docs) — free",
        "Redis in Action by Josiah Carlson (Manning)",
    ]),
    (re.compile(r"\bkafka\b", re.IGNORECASE), [
        "Apache Kafka Series (Stephane Maarek, Udemy)",
        "Apache Kafka official documentation — free",
        "Kafka: The Definitive Guide by Neha Narkhede et al. (O'Reilly)",
    ]),
    (re.compile(r"system design", re.IGNORECASE), [
        "Grokking the System Design Interview (educative.io)",
        "System Design Primer (github.com/donnemartin/system-design-primer) — free",
        "Designing Data-Intensive Applications by Martin Kleppmann (O'Reilly)",
    ]),
    (re.compile(r"\bseo\b|search engine optimization", re.IGNORECASE), [
        "SEO Training Course by Brian Dean (Backlinko) — free",
        "Google Search Central documentation — free",
        "SEO for Beginners: A Basic Search Engine Optimization Tutorial (Udemy)",
    ]),
    (re.compile(r"google analytics|\bga4\b", re.IGNORECASE), [
        "Google Analytics for Beginners (Google Skillshop) — free",
        "Google Analytics Individual Qualification (GAIQ) certification",
        "Google Analytics 4 (GA4) Certification Course (Udemy)",
    ]),
    (re.compile(r"social media marketing", re.IGNORECASE), [
        "Social Media Marketing Specialization (Northwestern, Coursera)",
        "Meta Social Media Marketing Professional Certificate",
        "Hootsuite Social Marketing Certification — free",
    ]),
    (re.compile(r"content marketing", re.IGNORECASE), [
        "Content Marketing Certification (HubSpot Academy) — free",
        "Content Marketing Institute resources — free",
        "Content Strategy for Professionals (Northwestern, Coursera)",
    ]),
    (re.compile(r"digital advertising|\bppc\b|paid (ads|media)", re.IGNORECASE), [
        "Google Ads Certification (Skillshop) — free",
        "Meta Blueprint Certification — free",
        "Digital Advertising: Planning, Buying, and Placement (Coursera)",
    ]),
    (re.compile(r"financial (modeling|modelling)", re.IGNORECASE), [
        "Financial Modeling & Valuation Analyst (FMVA) — Corporate Finance Institute",
        "Financial Modeling Fundamentals (Wall Street Prep)",
        "Financial Modeling in Excel for Beginners (Udemy)",
    ]),
    (re.compile(r"\bexcel\b", re.IGNORECASE), [
        "Excel Skills for Business Specialization (Macquarie, Coursera)",
        "Microsoft Excel official support & training — free",
        "Microsoft Office Specialist (MOS): Excel certification",
    ]),
    (re.compile(r"\btax(ation)?\b", re.IGNORECASE), [
        "US Federal Taxation Specialization (University of Illinois, Coursera)",
        "IRS.gov tax law resources — free",
        "Enrolled Agent (EA) certification study guide",
    ]),
    (re.compile(r"\baudit(ing)?\b", re.IGNORECASE), [
        "Auditing I: Conceptual Foundations of Auditing (Coursera)",
        "Certified Internal Auditor (CIA) certification",
        "The Institute of Internal Auditors resources",
    ]),
    (re.compile(r"project management|\bpmp\b", re.IGNORECASE), [
        "Google Project Management Professional Certificate (Coursera)",
        "Project Management Institute (PMI) resources — free",
        "PMP Certification Exam Prep (Udemy)",
    ]),
    (re.compile(r"strategic planning|business strategy", re.IGNORECASE), [
        "Strategic Management Specialization (Copenhagen Business School, Coursera)",
        "Harvard Business Review strategy articles — free",
        "Business Strategy: Business Model Canvas Analysis (Udemy)",
    ]),
]

_PROVIDER_TABLE = [
    (re.compile(r"\bdocker\b", re.IGNORECASE), "Docker + Udemy"),
    (re.compile(r"\bkubernetes\b|\bk8s\b", re.IGNORECASE), "Linux Foundation"),
    (re.compile(r"\bgraphql\b", re.IGNORECASE), "How to GraphQL"),
    (re.compile(r"\baws\b|\bcloud\b", re.IGNORECASE), "AWS Training & Certification"),
    (re.compile(r"\btypescript\b", re.IGNORECASE), "typescriptlang.org"),
    (re.compile(r"\breact\b", re.IGNORECASE), "React.dev"),
    (re.compile(r"\bpython\b", re.IGNORECASE), "Python Institute"),
    (re.compile(r"\bsql\b|\bpostgres(ql)?\b", re.IGNORECASE), "PostgreSQL Global Development Group"),
    (re.compile(r"machine learning|\bml\b", re.IGNORECASE), "Coursera + Google"),
    (re.compile(r"\bnode(\.js)?\b", re.IGNORECASE), "OpenJS Foundation"),
    (re.compile(r"\brust\b", re.IGNORECASE), "Rust Foundation"),
    (re.compile(r"\bgo(lang)?\b", re.IGNORECASE), "Go.dev"),
    (re.compile(r"ci/cd|\bci\b|\bcd\b|continuous integration|continuous delivery", re.IGNORECASE), "GitHub"),
    (re.compile(r"\bterraform\b", re.IGNORECASE), "HashiCorp"),
    (re.compile(r"\bredis\b", re.IGNORECASE), "Redis Ltd."),
    (re.compile(r"\bkafka\b", re.IGNORECASE), "Confluent"),
    (re.compile(r"system design", re.IGNORECASE), "Educative"),
    (re.compile(r"\bseo\b|search engine optimization", re.IGNORECASE), "Backlinko / Google"),
    (re.compile(r"google analytics|\bga4\b", re.IGNORECASE), "Google Skillshop"),
    (re.compile(r"social media marketing", re.IGNORECASE), "Meta / Hootsuite"),
    (re.compile(r"content marketing", re.IGNORECASE), "HubSpot Academy"),
    (re.compile(r"digital advertising|\bppc\b|paid (ads|media)", re.IGNORECASE), "Google Ads / Meta Blueprint"),
    (re.compile(r"financial (modeling|modelling)", re.IGNORECASE), "Corporate Finance Institute"),
    (re.compile(r"\bexcel\b", re.IGNORECASE), "Microsoft"),
    (re.compile(r"\btax(ation)?\b", re.IGNORECASE), "IRS / University of Illinois"),
    (re.compile(r"\baudit(ing)?\b", re.IGNORECASE), "Institute of Internal Auditors"),
    (re.compile(r"project management|\bpmp\b", re.IGNORECASE), "PMI / Google"),
    (re.compile(r"strategic planning|business strategy", re.IGNORECASE), "Harvard Business Review"),
]


def get_resources(skill: str) -> list[dict]:
    for pattern, resources in _RESOURCE_TABLE:
        if pattern.search(skill or ""):
            provider = get_provider(skill)
            return [{"name": r, "type": get_resource_type(skill), "provider": provider} for r in resources]
    return [
        {"name": f'Search "{skill} tutorial" on YouTube', "type": "Video", "provider": "YouTube"},
        {"name": f"Official documentation for {skill}", "type": "Docs", "provider": "Official docs"},
        {"name": f'Search "{skill} course" on Udemy — filter by highest rated', "type": "Course", "provider": "Udemy"},
    ]


def get_resource_type(skill: str) -> str:
    skill_lower = (skill or "").lower()
    if re.search(r"cka|cks|aws|gcp|azure|terraform associate|\bpmp\b|\bcia\b|\bea\b|gaiq", skill_lower):
        return "Cert"
    return "Course"


def get_provider(skill: str) -> str:
    for pattern, provider in _PROVIDER_TABLE:
        if pattern.search(skill or ""):
            return provider
    return "Multiple providers"


# ---------------------------------------------------------------------------
# Profession detection — a keyword-scoring heuristic, not AI. Deliberately
# simple and auditable: each candidate profession category has a list of
# regex patterns; whichever category scores the most matches against the
# candidate's target role/industry/skills/resume text wins. No match at all
# falls back to "general" — which is itself profession-neutral content, never
# software engineering by default.
# ---------------------------------------------------------------------------

_PROFESSION_KEYWORDS = {
    "software_engineering": [
        r"software", r"\bdeveloper\b", r"\bengineer(ing)?\b", r"programming", r"\bdocker\b", r"\bkubernetes\b",
        r"\bapi\b", r"\bbackend\b", r"\bfrontend\b", r"full.?stack", r"\bdevops\b", r"\bsql\b", r"\bpython\b",
        r"javascript", r"\bjava\b", r"\breact\b", r"\bnode(\.js)?\b", r"\bgit\b", r"cloud comput",
        r"\bci/cd\b", r"computer science",
    ],
    "marketing": [
        r"\bmarketing\b", r"\bseo\b", r"content strategy", r"social media", r"\bbrand(ing)?\b", r"\bcampaign\b",
        r"google analytics", r"advertising", r"digital marketing", r"copywriting", r"\bcrm\b", r"content marketing",
    ],
    "accounting": [
        r"\baccounting\b", r"\baccountant\b", r"\baudit(ing)?\b", r"taxation", r"\btax\b", r"bookkeep",
        r"\bgaap\b", r"financial reporting", r"reconciliation", r"quickbooks", r"\bpayroll\b", r"\bledger\b",
    ],
    "business_administration": [
        r"business administration", r"business analyst", r"operations manage", r"strategic planning",
        r"project management", r"\bmba\b", r"management consult", r"business development", r"stakeholder",
        r"\bpmp\b", r"business strategy",
    ],
    "data_science": [
        r"data scien", r"data analy", r"machine learning", r"\bml\b\W", r"\betl\b", r"data visualization",
        r"statistics", r"\bpandas\b", r"\btableau\b", r"\bpower ?bi\b",
    ],
}

PROFESSION_LABELS = {
    "software_engineering": "Software Engineering",
    "marketing": "Marketing",
    "accounting": "Accounting",
    "business_administration": "Business Administration",
    "data_science": "Data Science",
    "general": "General Professional",
}


def detect_profession_category(
    target_role: str | None, industry: str | None, resume_skills: list[str],
    missing_skills: list[str], resume_text: str = "",
) -> str:
    """Best-effort profession category from whatever signal is available —
    never assumes software engineering just because that happens to be the
    first entry in the lookup table. Returns "general" when nothing matches
    clearly, which has its own profession-neutral content, not a tech default."""
    blob = " ".join(filter(None, [
        target_role or "", industry or "", " ".join(resume_skills or []),
        " ".join(missing_skills or []), (resume_text or "")[:1500],
    ])).lower()

    if not blob.strip():
        return "general"

    scores = {}
    for category, patterns in _PROFESSION_KEYWORDS.items():
        score = sum(1 for pattern in patterns if re.search(pattern, blob))
        if score:
            scores[category] = score

    if not scores:
        return "general"
    return max(scores, key=scores.get)


def _skill_topic(skill: str, priority: str, category_label: str) -> dict:
    hours = {"critical": 30, "high": 15, "medium": 8}[priority]
    return {
        "key": f"skill-{skill.lower().replace(' ', '-')}",
        "title": skill,
        "category": category_label,
        "why_it_matters": "Identified as a gap against the target role's requirements — closing it directly improves job readiness for this position.",
        "learning_objectives": [
            f"Explain the core concepts of {skill} and where it fits in a real project.",
            f"Build a small working example using {skill} without following a tutorial step-by-step.",
        ],
        "resources": get_resources(skill),
        "projects": [f"Build a small project that meaningfully uses {skill} and add it to your portfolio."],
        "exercises": [f"Complete 2-3 focused practice exercises specifically on {skill}."],
        "estimated_hours": hours,
        "priority": priority,
    }


# ---------------------------------------------------------------------------
# Foundation topic banks, one per detected profession category. Each bank
# stands in for "what someone needs before anything else" in that field —
# genuinely different content per category, not a single fixed list reused
# for everyone regardless of what they actually do.
# ---------------------------------------------------------------------------

_FOUNDATION_BANKS = {
    "software_engineering": [
        {
            "key": "foundation-git", "title": "Version control with Git", "category": "Tools & Software",
            "why_it_matters": "Every professional engineering team collaborates through Git — it's assumed baseline knowledge in any technical interview.",
            "learning_objectives": ["Create branches, resolve merge conflicts, and write clear commit history.", "Use pull requests as part of a real code review workflow."],
            "resources": [
                {"name": "Pro Git (git-scm.com/book) — free", "type": "Free", "provider": "Git"},
                {"name": "Learn Git Branching (learngitbranching.js.org) — free", "type": "Free", "provider": "Community"},
            ],
            "projects": ["Contribute a small fix to an open-source repo via a pull request."],
            "exercises": ["Practice rebasing and resolving a merge conflict on a throwaway repo."],
            "estimated_hours": 6, "priority": "high",
        },
        {
            "key": "foundation-clean-code", "title": "Writing clean, testable code", "category": "Code Quality",
            "why_it_matters": "Code quality and testability are what separates a junior submission from a hire-ready one in technical screens.",
            "learning_objectives": ["Write functions with single responsibility and clear naming.", "Write unit tests that actually catch regressions."],
            "resources": [
                {"name": "Clean Code by Robert C. Martin", "type": "Book", "provider": "Prentice Hall"},
                {"name": "Testing your language's standard test framework — official docs", "type": "Docs", "provider": "Official docs"},
            ],
            "projects": ["Refactor an old personal project with a real test suite."],
            "exercises": ["Practice test-driven development on a small kata."],
            "estimated_hours": 10, "priority": "high",
        },
        {
            "key": "foundation-debugging", "title": "Debugging & problem-solving fundamentals", "category": "Problem Solving",
            "why_it_matters": "Interviewers explicitly test how you reason under uncertainty — this is a core, role-agnostic hiring signal.",
            "learning_objectives": ["Use a debugger instead of print statements for non-trivial bugs.", "Systematically narrow down the root cause of a failure."],
            "resources": [
                {"name": "Your language/runtime's official debugger docs", "type": "Docs", "provider": "Official docs"},
                {"name": "Grokking Algorithms by Aditya Bhargava", "type": "Book", "provider": "Manning"},
            ],
            "projects": ["Deliberately break a project and practice root-causing it methodically."],
            "exercises": ["Solve 3-5 debugging-focused coding challenges."],
            "estimated_hours": 8, "priority": "medium",
        },
        {
            "key": "foundation-cs-fundamentals", "title": "Core data structures & algorithms", "category": "Computer Science Fundamentals",
            "why_it_matters": "Nearly every technical interview, regardless of role, still probes fundamental CS reasoning.",
            "learning_objectives": ["Explain time/space complexity of common operations.", "Implement and reason about arrays, hash maps, trees, and graphs."],
            "resources": [
                {"name": "Grokking Algorithms by Aditya Bhargava", "type": "Book", "provider": "Manning"},
                {"name": "NeetCode 150 (neetcode.io) — free", "type": "Free", "provider": "NeetCode"},
            ],
            "projects": ["Implement a small data structure (e.g. LRU cache) from scratch."],
            "exercises": ["Solve 10 easy/medium data structure problems."],
            "estimated_hours": 20, "priority": "high",
        },
    ],
    "business_administration": [
        {
            "key": "foundation-biz-communication", "title": "Business communication & professional writing", "category": "Communication",
            "why_it_matters": "Managers and analysts are judged heavily on how clearly they write memos, reports, and proposals — it's a daily, visible skill.",
            "learning_objectives": ["Write a concise executive summary that leads with the recommendation.", "Structure a business memo so a busy stakeholder can skim it in under a minute."],
            "resources": [
                {"name": "Business Writing Specialization (University of Colorado, Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "HBR Guide to Better Business Writing (Harvard Business Review)", "type": "Book", "provider": "Harvard Business Review"},
            ],
            "projects": ["Write a one-page executive summary for a real or hypothetical business decision."],
            "exercises": ["Rewrite a rambling paragraph from a real report into 3 clear bullet points."],
            "estimated_hours": 6, "priority": "high",
        },
        {
            "key": "foundation-financial-literacy", "title": "Financial literacy for managers", "category": "Financial Literacy",
            "why_it_matters": "Every business decision eventually gets evaluated in financial terms — reading a P&L or budget confidently is assumed baseline knowledge.",
            "learning_objectives": ["Read and interpret a profit & loss statement and a balance sheet.", "Calculate and explain basic KPIs like margin, ROI, and burn rate."],
            "resources": [
                {"name": "Finance for Non-Financial Managers (Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "Investopedia's financial statement guides — free", "type": "Free", "provider": "Investopedia"},
            ],
            "projects": ["Analyze a public company's income statement and summarize its financial health in one page."],
            "exercises": ["Calculate gross margin, net margin, and ROI from a sample P&L."],
            "estimated_hours": 10, "priority": "high",
        },
        {
            "key": "foundation-strategic-thinking", "title": "Strategic thinking & decision-making frameworks", "category": "Strategy",
            "why_it_matters": "Case interviews and real strategy work both expect structured frameworks (SWOT, Porter's Five Forces, etc.) rather than gut-feel reasoning.",
            "learning_objectives": ["Apply a SWOT or Porter's Five Forces analysis to a real business scenario.", "Structure an ambiguous business problem into a clear decision tree."],
            "resources": [
                {"name": "Strategic Management Specialization (Copenhagen Business School, Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "Harvard Business Review strategy articles — free", "type": "Free", "provider": "Harvard Business Review"},
            ],
            "projects": ["Write a SWOT analysis and strategic recommendation for a company you know well."],
            "exercises": ["Practice 2-3 business case questions using a structured framework."],
            "estimated_hours": 10, "priority": "medium",
        },
        {
            "key": "foundation-business-analytics", "title": "Business analytics & data-driven decision making", "category": "Analytics",
            "why_it_matters": "Modern business roles expect comfort with spreadsheets and dashboards to justify decisions with data, not just intuition.",
            "learning_objectives": ["Build a pivot table to summarize a real business dataset.", "Interpret a dashboard and identify the key driver behind a trend."],
            "resources": [
                {"name": "Excel Skills for Business Specialization (Macquarie, Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "Google Data Analytics Professional Certificate (Coursera)", "type": "Course", "provider": "Coursera"},
            ],
            "projects": ["Build a simple KPI dashboard from a sample sales or operations dataset."],
            "exercises": ["Practice building 2-3 pivot tables from a raw spreadsheet export."],
            "estimated_hours": 12, "priority": "high",
        },
    ],
    "marketing": [
        {
            "key": "foundation-marketing-fundamentals", "title": "Marketing fundamentals & the marketing funnel", "category": "Marketing Foundations",
            "why_it_matters": "Every marketing specialization (SEO, social, paid ads) sits on top of the same core funnel and positioning concepts.",
            "learning_objectives": ["Map a customer journey through awareness, consideration, and conversion.", "Write a clear value proposition for a product or service."],
            "resources": [
                {"name": "Google Digital Marketing & E-commerce Certificate (Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "HubSpot Academy's Marketing courses — free", "type": "Free", "provider": "HubSpot Academy"},
            ],
            "projects": ["Map the full marketing funnel for a real product, from awareness to retention."],
            "exercises": ["Write 3 value proposition statements for the same product targeting different audiences."],
            "estimated_hours": 8, "priority": "high",
        },
        {
            "key": "foundation-marketing-analytics", "title": "Marketing analytics & KPIs", "category": "Analytics",
            "why_it_matters": "Marketing decisions are expected to be backed by data — CTR, conversion rate, CAC, and ROAS are everyday vocabulary.",
            "learning_objectives": ["Set up and read a Google Analytics 4 report.", "Calculate and explain CAC, conversion rate, and ROAS."],
            "resources": [
                {"name": "Google Analytics for Beginners (Google Skillshop) — free", "type": "Free", "provider": "Google Skillshop"},
                {"name": "Google Analytics 4 (GA4) Certification Course (Udemy)", "type": "Course", "provider": "Udemy"},
            ],
            "projects": ["Set up a GA4 property (or use a demo account) and build a simple performance report."],
            "exercises": ["Calculate CAC and ROAS from a sample campaign spend/revenue dataset."],
            "estimated_hours": 10, "priority": "high",
        },
        {
            "key": "foundation-content-branding", "title": "Content strategy & brand voice", "category": "Content & Branding",
            "why_it_matters": "Consistent messaging across channels is what separates professional marketing from ad-hoc posting.",
            "learning_objectives": ["Define a brand voice and apply it consistently across two different content formats.", "Plan a content calendar aligned to a campaign goal."],
            "resources": [
                {"name": "Content Marketing Certification (HubSpot Academy) — free", "type": "Free", "provider": "HubSpot Academy"},
                {"name": "Content Marketing Institute resources — free", "type": "Free", "provider": "Content Marketing Institute"},
            ],
            "projects": ["Build a one-month content calendar for a real or hypothetical brand."],
            "exercises": ["Write the same announcement in 3 different brand voices (playful, corporate, minimal)."],
            "estimated_hours": 8, "priority": "medium",
        },
        {
            "key": "foundation-marketing-tools", "title": "Core marketing tools & platforms", "category": "Tools & Platforms",
            "why_it_matters": "Hands-on comfort with the actual platforms (ad managers, CRM, email tools) is what hiring managers screen for beyond theory.",
            "learning_objectives": ["Navigate a CRM to segment an audience for a campaign.", "Set up a basic campaign in a paid ad platform's interface."],
            "resources": [
                {"name": "Meta Blueprint Certification — free", "type": "Free", "provider": "Meta"},
                {"name": "Google Ads Certification (Skillshop) — free", "type": "Free", "provider": "Google Skillshop"},
            ],
            "projects": ["Set up a mock campaign in a free-tier ad platform account, targeting a defined audience."],
            "exercises": ["Segment a sample customer list into 3 meaningful audience groups."],
            "estimated_hours": 8, "priority": "medium",
        },
    ],
    "accounting": [
        {
            "key": "foundation-accounting-fundamentals", "title": "Accounting fundamentals & GAAP principles", "category": "Accounting Foundations",
            "why_it_matters": "GAAP (or IFRS) principles are the shared language every accounting role operates in — non-negotiable baseline knowledge.",
            "learning_objectives": ["Explain the accounting equation and double-entry bookkeeping.", "Identify which GAAP principle applies to a given transaction."],
            "resources": [
                {"name": "Accounting: Principles of Financial Accounting (Coursera, Wharton)", "type": "Course", "provider": "Coursera"},
                {"name": "AccountingCoach.com — free", "type": "Free", "provider": "AccountingCoach"},
            ],
            "projects": ["Record a month of sample transactions using double-entry bookkeeping by hand."],
            "exercises": ["Classify 10 sample transactions by which GAAP principle governs them."],
            "estimated_hours": 12, "priority": "high",
        },
        {
            "key": "foundation-accounting-software", "title": "Spreadsheet & accounting software proficiency", "category": "Tools & Software",
            "why_it_matters": "Excel and tools like QuickBooks are used daily in nearly every accounting role — fluency is assumed, not taught on the job.",
            "learning_objectives": ["Build a reconciliation spreadsheet using formulas, not manual entry.", "Record and categorize transactions in QuickBooks or a similar tool."],
            "resources": [
                {"name": "Excel Skills for Business Specialization (Macquarie, Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "QuickBooks Online official training — free", "type": "Free", "provider": "Intuit"},
            ],
            "projects": ["Build a bank reconciliation spreadsheet from a sample statement and ledger."],
            "exercises": ["Practice VLOOKUP/XLOOKUP and SUMIF formulas on a sample transaction dataset."],
            "estimated_hours": 10, "priority": "high",
        },
        {
            "key": "foundation-financial-statements", "title": "Financial statement literacy", "category": "Financial Literacy",
            "why_it_matters": "Preparing and interpreting the income statement, balance sheet, and cash flow statement is the core deliverable of most accounting roles.",
            "learning_objectives": ["Prepare a basic income statement and balance sheet from a trial balance.", "Explain how the three financial statements connect to each other."],
            "resources": [
                {"name": "Financial Accounting Specialization (University of Pennsylvania, Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "Investopedia's financial statement guides — free", "type": "Free", "provider": "Investopedia"},
            ],
            "projects": ["Prepare a full set of financial statements from a sample trial balance."],
            "exercises": ["Trace how a single transaction flows through all three financial statements."],
            "estimated_hours": 12, "priority": "high",
        },
        {
            "key": "foundation-reconciliation", "title": "Reconciliation & attention to detail practices", "category": "Accuracy & Controls",
            "why_it_matters": "Errors in reconciliation directly affect financial reporting accuracy — this is one of the most closely reviewed skills in an accounting interview.",
            "learning_objectives": ["Perform a bank reconciliation and identify the source of a discrepancy.", "Apply a systematic checklist to catch common data-entry errors."],
            "resources": [
                {"name": "Auditing I: Conceptual Foundations of Auditing (Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "The Institute of Internal Auditors resources", "type": "Free", "provider": "IIA"},
            ],
            "projects": ["Reconcile a sample bank statement against a ledger with 3-4 deliberate discrepancies."],
            "exercises": ["Find and correct 5 seeded errors in a sample set of journal entries."],
            "estimated_hours": 8, "priority": "medium",
        },
    ],
    "general": [
        {
            "key": "foundation-professional-communication", "title": "Professional communication & writing", "category": "Communication",
            "why_it_matters": "Clear written and verbal communication is a baseline expectation across essentially every professional role.",
            "learning_objectives": ["Write a concise, well-structured professional email or report.", "Present an idea clearly in under two minutes."],
            "resources": [
                {"name": "Business Writing Specialization (University of Colorado, Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "Toastmasters International resources — free", "type": "Free", "provider": "Toastmasters"},
            ],
            "projects": ["Write and deliver a two-minute summary of a project you've worked on."],
            "exercises": ["Rewrite a long, unclear paragraph into 3 clear sentences."],
            "estimated_hours": 5, "priority": "high",
        },
        {
            "key": "foundation-time-management", "title": "Time management & prioritization", "category": "Productivity",
            "why_it_matters": "The ability to prioritize competing deadlines is a universal signal of professional readiness, regardless of field.",
            "learning_objectives": ["Prioritize a list of tasks using a framework like Eisenhower's matrix.", "Build a realistic weekly plan that accounts for interruptions."],
            "resources": [
                {"name": "Work Smarter, Not Harder Specialization (UC Irvine, Coursera)", "type": "Course", "provider": "Coursera"},
                {"name": "Getting Things Done by David Allen", "type": "Book", "provider": "Penguin"},
            ],
            "projects": ["Plan and track a real week using a prioritization framework, then review what worked."],
            "exercises": ["Sort a list of 10 mixed tasks into an Eisenhower matrix."],
            "estimated_hours": 4, "priority": "medium",
        },
        {
            "key": "foundation-domain-tools", "title": "Core tools & software for your field", "category": "Tools & Software",
            "why_it_matters": "Every field has a small set of tools practitioners are expected to already be comfortable with before day one.",
            "learning_objectives": ["Identify the 2-3 tools most commonly required in job postings for your target role.", "Reach basic working proficiency in the most important one."],
            "resources": [
                {"name": "LinkedIn Learning's field-specific tool courses", "type": "Course", "provider": "LinkedIn Learning"},
                {"name": "Search official documentation/training for your field's leading tool — free", "type": "Free", "provider": "Official docs"},
            ],
            "projects": ["Complete a small real task using the primary tool for your target field."],
            "exercises": ["Work through that tool's official beginner tutorial end-to-end."],
            "estimated_hours": 8, "priority": "high",
        },
        {
            "key": "foundation-domain-knowledge", "title": "Foundational domain knowledge", "category": "Domain Knowledge",
            "why_it_matters": "Grounding in the fundamentals of your target field lets you speak credibly in interviews, not just list skills.",
            "learning_objectives": ["Explain the core concepts and terminology of your target field to someone unfamiliar with it.", "Identify the 3-5 biggest trends currently shaping the field."],
            "resources": [
                {"name": "An introductory course or certificate relevant to your target field (Coursera/edX)", "type": "Course", "provider": "Coursera/edX"},
                {"name": "Leading industry publications/blogs for your field — free", "type": "Free", "provider": "Various"},
            ],
            "projects": ["Write a one-page primer on your target field as if explaining it to a career-changer."],
            "exercises": ["Summarize 3 recent articles from a leading publication in your target field."],
            "estimated_hours": 6, "priority": "medium",
        },
    ],
}

# The 3 Job Ready topics that genuinely don't vary by profession — interview
# readiness, portfolio storytelling, and mock-practice apply the same way
# whether you're closing a business case or shipping a feature.
_JOB_READY_SHARED_TOPICS = [
    {
        "key": "job-ready-portfolio", "title": "Portfolio & project storytelling", "category": "Career Readiness",
        "why_it_matters": "Hiring managers screen on demonstrated, explainable work — not just a skills list.",
        "learning_objectives": ["Present a project's impact, trade-offs, and your specific contributions clearly.", "Curate 2-3 portfolio pieces that map directly to the target role."],
        "resources": [{"name": "Your target companies' publications/case studies — free", "type": "Free", "provider": "Various"}],
        "projects": ["Write a case-study writeup for your strongest piece of work."],
        "exercises": ["Practice a 2-minute verbal walkthrough of your best project or case."],
        "estimated_hours": 6, "priority": "medium",
    },
    {
        "key": "job-ready-interview-prep", "title": "Behavioral interview readiness", "category": "Career Readiness",
        "why_it_matters": "Behavioral rounds are a real, often deciding part of the hiring process — preparation compounds confidence.",
        "learning_objectives": ["Structure answers using a framework like STAR.", "Have 4-5 concrete stories ready covering conflict, failure, ownership, and impact."],
        "resources": [{"name": "Cracking the PM/Coding Interview behavioral chapters", "type": "Book", "provider": "CareerCup"}],
        "projects": ["Write out and rehearse 5 STAR-format stories from your own experience."],
        "exercises": ["Run a mock behavioral interview with a friend or record yourself."],
        "estimated_hours": 6, "priority": "high",
    },
    {
        "key": "job-ready-mock-interviews", "title": "Mock interviews & feedback loops", "category": "Career Readiness",
        "why_it_matters": "Interview performance is a skill in itself — realistic practice under pressure closes the gap between knowing and performing.",
        "learning_objectives": ["Complete a mock interview and identify specific weak points.", "Iterate on weak areas with targeted practice, not general review."],
        "resources": [{"name": "This platform's AI Interview Practice", "type": "Free", "provider": "ResumeIQ"}],
        "projects": ["Complete at least 2 full mock interviews and act on the feedback."],
        "exercises": ["Time-box and complete one mock interview per week."],
        "estimated_hours": 4, "priority": "critical",
    },
]

# The 4th Job Ready slot — a capstone that IS profession-specific, since
# "apply what you learned to something real" looks completely different for
# a system design exercise versus a business case study.
_CAPSTONE_BY_CATEGORY = {
    "software_engineering": {
        "key": "job-ready-system-design", "title": "System design & architecture fundamentals", "category": "Technical Depth",
        "why_it_matters": "Job-ready candidates can reason about trade-offs at a system level, not just write working code.",
        "learning_objectives": ["Design a system given rough requirements and articulate trade-offs.", "Reason about scaling, caching, and data consistency at a high level."],
        "resources": [
            {"name": "System Design Primer (github.com/donnemartin/system-design-primer) — free", "type": "Free", "provider": "Community"},
            {"name": "Grokking the System Design Interview", "type": "Course", "provider": "Educative"},
        ],
        "projects": ["Write a design doc for a system relevant to your target role."],
        "exercises": ["Practice 2-3 mock system design prompts out loud or in writing."],
        "estimated_hours": 15, "priority": "high",
    },
    "business_administration": {
        "key": "job-ready-business-case", "title": "Business case study & strategic proposal development", "category": "Applied Strategy",
        "why_it_matters": "Case interviews and real strategy roles both expect you to turn ambiguous business problems into a structured, defensible recommendation.",
        "learning_objectives": ["Structure an ambiguous business problem into a clear analysis and recommendation.", "Defend a strategic proposal against likely counterarguments."],
        "resources": [
            {"name": "Case Interview Prep (CaseCoach or IGotAnOffer) — free tier available", "type": "Free", "provider": "Various"},
            {"name": "Harvard Business School case studies (HBR)", "type": "Article", "provider": "Harvard Business Review"},
        ],
        "projects": ["Write a full strategic proposal (problem, analysis, recommendation) for a real or hypothetical company."],
        "exercises": ["Practice 2-3 business case prompts out loud or in writing."],
        "estimated_hours": 15, "priority": "high",
    },
    "marketing": {
        "key": "job-ready-campaign-case-study", "title": "Campaign case study & marketing plan development", "category": "Applied Marketing",
        "why_it_matters": "The strongest marketing candidates can walk through a full campaign — strategy, execution, and measured results — not just list channels they've used.",
        "learning_objectives": ["Build a full campaign plan from objective through to measurement.", "Present a campaign's results and what you'd change next time."],
        "resources": [
            {"name": "HubSpot Academy's campaign planning courses — free", "type": "Free", "provider": "HubSpot Academy"},
            {"name": "Real-world campaign breakdowns (Marketing Examples, swiped.co) — free", "type": "Free", "provider": "Various"},
        ],
        "projects": ["Write a full marketing plan (objective, audience, channels, budget, KPIs) for a real or hypothetical product launch."],
        "exercises": ["Practice presenting a campaign's results and lessons learned in under 2 minutes."],
        "estimated_hours": 12, "priority": "high",
    },
    "accounting": {
        "key": "job-ready-financial-case-study", "title": "Financial analysis case study & audit simulation", "category": "Applied Accounting",
        "why_it_matters": "Accounting interviews frequently include a practical case — analyzing real statements or walking through an audit scenario — not just theory questions.",
        "learning_objectives": ["Analyze a real company's financial statements and identify a red flag.", "Walk through a simplified audit scenario end-to-end."],
        "resources": [
            {"name": "Financial Statement Analysis Specialization (Coursera)", "type": "Course", "provider": "Coursera"},
            {"name": "SEC EDGAR public filings for practice — free", "type": "Free", "provider": "SEC"},
        ],
        "projects": ["Analyze a public company's 10-K and write a one-page financial health assessment."],
        "exercises": ["Work through a simplified audit-scenario case study."],
        "estimated_hours": 12, "priority": "high",
    },
    "data_science": {
        "key": "job-ready-data-case-study", "title": "End-to-end data analysis case study", "category": "Applied Data Science",
        "why_it_matters": "Job-ready data candidates can take a messy, real dataset from question to actionable recommendation, not just run isolated notebook exercises.",
        "learning_objectives": ["Take a real dataset from cleaning through to a clear, decision-ready finding.", "Communicate a technical finding to a non-technical audience."],
        "resources": [
            {"name": "Kaggle datasets & competitions — free", "type": "Free", "provider": "Kaggle"},
            {"name": "Storytelling with Data by Cole Nussbaumer Knaflic", "type": "Book", "provider": "Wiley"},
        ],
        "projects": ["Complete a full analysis on a public dataset and write it up as a decision memo."],
        "exercises": ["Practice explaining one finding from your analysis to someone with no data background."],
        "estimated_hours": 15, "priority": "high",
    },
    "general": {
        "key": "job-ready-capstone", "title": "Capstone project or real-world case study", "category": "Applied Practice",
        "why_it_matters": "Applying everything you've learned to one real, end-to-end piece of work is what actually proves job-readiness, more than any single topic on its own.",
        "learning_objectives": ["Complete one substantial project or case study relevant to your target role from start to finish.", "Present the work's outcome and what you'd do differently."],
        "resources": [{"name": "A real or simulated project brief relevant to your target field", "type": "Free", "provider": "Various"}],
        "projects": ["Complete one capstone project or case study end-to-end and document the outcome."],
        "exercises": ["Practice presenting the capstone's outcome in under 2 minutes."],
        "estimated_hours": 12, "priority": "high",
    },
}


def _job_ready_topics(category: str) -> list[dict]:
    capstone = _CAPSTONE_BY_CATEGORY.get(category, _CAPSTONE_BY_CATEGORY["general"])
    return [capstone] + _JOB_READY_SHARED_TOPICS


def _generic_current_gap(skill: str) -> str:
    return (
        f"Not clearly demonstrated on your resume or in prior sessions — this roadmap treats {skill} as new "
        "ground rather than assuming existing depth."
    )


def _generic_milestones(skill: str) -> dict:
    return {
        "beginner": f"You understand the core concepts of {skill} and can follow a guided tutorial without getting stuck.",
        "intermediate": f"You can build a small project with {skill} mostly unassisted, referring to docs when needed.",
        "advanced": f"You can debug non-trivial issues in {skill} and explain the real trade-offs of using it.",
    }


def _generic_quiz(skill: str) -> list[dict]:
    return [
        {
            "question": f"What's the best way to confirm you've actually learned {skill}, not just read about it?",
            "options": [
                "Watching more videos about it",
                f"Building something real with {skill} and explaining your choices",
                "Memorizing the official documentation",
                "Skipping straight to using it in an interview",
            ],
            "correct_index": 1,
            "explanation": "Hands-on application — not passive consumption — is what actually builds and proves competence.",
        },
        {
            "question": f"When you get stuck on a {skill} problem you haven't seen before, what should you do first?",
            "options": [
                "Give up and move to a different topic",
                "Guess randomly until something works",
                "Break the problem down and check the official docs or source for how it's meant to work",
                "Wait for someone else to solve it",
            ],
            "correct_index": 2,
            "explanation": "Systematically narrowing down a problem using authoritative sources is the core debugging skill that separates guided learning from real competence.",
        },
    ]


def _add_depth_fields(stages: list[dict]) -> list[dict]:
    """Fills in current_gap/milestones/quiz on every topic with generic, deterministic
    content — keeps the rule-based fallback's shape identical to the AI path's (see
    learning_roadmap_ai.py's ROADMAP_SCHEMA) without hand-authoring this content for
    every topic in every profession bank. Builds new dicts rather than mutating in
    place — the topic bank dicts are shared module-level data reused across every
    call/request, so mutating them in place would leak state between unrelated
    roadmaps."""
    new_stages = []
    for stage in stages:
        new_topics = []
        for topic in stage["topics"]:
            title = topic["title"]
            new_topics.append({
                **topic,
                "current_gap": topic.get("current_gap") or _generic_current_gap(title),
                "milestones": topic.get("milestones") or _generic_milestones(title),
                "quiz": topic.get("quiz") or _generic_quiz(title),
            })
        new_stages.append({**stage, "topics": new_topics})
    return new_stages


def build_roadmap(
    missing_skills: list[str], resume_skills: list[str],
    target_role: str | None = None, industry: str | None = None, resume_text: str = "",
) -> dict:
    """Deterministic 4-stage roadmap: Foundation and Job Ready are picked
    from the detected profession's topic bank (never a fixed software-
    engineering list for every user); Intermediate and Advanced are built
    from the identified skill gaps (first half = core/Intermediate, second
    half = differentiating/Advanced), tagged with a priority for the UI."""
    category = detect_profession_category(target_role, industry, resume_skills, missing_skills, resume_text)
    category_label = PROFESSION_LABELS.get(category, PROFESSION_LABELS["general"])
    foundation_topics = _FOUNDATION_BANKS.get(category, _FOUNDATION_BANKS["general"])
    job_ready_topics = _job_ready_topics(category)

    gaps = [s for s in (missing_skills or []) if s]
    midpoint = math.ceil(len(gaps) / 2)
    intermediate_gaps = gaps[:midpoint]
    advanced_gaps = gaps[midpoint:]
    skill_category_label = f"{category_label} Skills"

    stages = [
        {
            "stage": "Foundation",
            "description": f"Core fundamentals expected of any professional in {category_label.lower()}, independent of the specific role.",
            "estimated_duration": "2-3 weeks",
            "milestone": f"You can confidently operate as a {category_label.lower()} professional on the fundamentals covered here.",
            "topics": foundation_topics,
        },
        {
            "stage": "Intermediate",
            "description": "The core, everyday skills expected for the target role.",
            "estimated_duration": "3-5 weeks",
            "milestone": "You can independently handle the core, everyday responsibilities of the target role.",
            "topics": [_skill_topic(skill, "high", skill_category_label) for skill in intermediate_gaps]
            or [_skill_topic(skill, "medium", skill_category_label) for skill in resume_skills[:2]],
        },
        {
            "stage": "Advanced",
            "description": "Specialized, differentiating skills that separate a strong candidate from an average one for this role.",
            "estimated_duration": "3-5 weeks",
            "milestone": "You've closed the identified skill gaps and can speak to them credibly in an interview.",
            "topics": [_skill_topic(skill, "critical", skill_category_label) for skill in advanced_gaps]
            or [_skill_topic(skill, "medium", skill_category_label) for skill in resume_skills[2:4]],
        },
        {
            "stage": "Job Ready",
            "description": "Interview readiness, portfolio polish, and applied practice — the final stretch before applying.",
            "estimated_duration": "2-3 weeks",
            "milestone": "You're ready to apply and interview for the target role with confidence.",
            "topics": job_ready_topics,
        },
    ]

    return {
        "stages": _add_depth_fields(stages),
        "detected_profession": target_role or category_label,
        "detected_industry": industry or "",
    }
