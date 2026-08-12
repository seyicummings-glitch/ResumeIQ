"""
Rule-based learning roadmap builder — the no-AI fallback for
app/services/learning_roadmap_ai.py. No machine learning here: resource
suggestions and stage groupings are selected deterministically from fixed
lookup tables keyed by regex/keyword matches. Mirrors the style of
matching_engine.py: pure functions, no FastAPI/SQLAlchemy imports.

Produces {"stages": [...], "detected_profession": str, "detected_industry": str}
— the same shape the AI path returns (see learning_roadmap_ai.py's
ROADMAP_SCHEMA) so the route layer and frontend don't need to special-case
which path generated the roadmap.

Every topic in every stage is built from the caller's actual missing_skills
(computed upstream by matching_engine.py from the candidate's resume vs. the
job description they're targeting) — never from a fixed, pre-written topic
list. Earlier versions of this module filled the Foundation and Job Ready
stages from a hand-authored bank of topics per detected profession (e.g.
"Version control with Git" for anyone flagged as software engineering); that
meant every user in a given category saw the same handful of topics
regardless of what their specific resume/JD pairing actually showed was
missing. detect_profession_category() is still used, but purely to label the
roadmap and group/tag the real skill-gap topics — it never determines what
topics appear. Two users in the same profession with different skill gaps
now get genuinely different roadmaps; a user with zero skill gaps gets an
honest "nothing critical to close" topic instead of generic filler content.
"""
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
    "healthcare": [
        r"patient care", r"clinical", r"\bnurs(e|ing)\b", r"\bhipaa\b", r"\behr\b", r"\bemr\b", r"medical cod",
        r"medical bill", r"phlebotomy", r"triage", r"pharmacology", r"healthcare", r"physician", r"\bcpr\b",
        r"\bacls\b", r"\bbls\b", r"infection control",
    ],
    "human_resources": [
        r"\brecruit(ing|er|ment)?\b", r"talent acquisition", r"employee relations", r"\bhris\b",
        r"compensation (&|and) benefits", r"onboarding", r"human resources", r"\bhr\b generalist",
        r"labor relations", r"succession planning",
    ],
    "legal": [
        r"litigation", r"legal research", r"paralegal", r"\battorney\b", r"contract (drafting|review)",
        r"regulatory compliance", r"corporate law", r"westlaw", r"lexisnexis", r"\bjd\b", r"\bcounsel\b",
    ],
    "design": [
        r"graphic design", r"\bux\b", r"\bui\b design", r"\bfigma\b", r"wirefram", r"prototyp",
        r"adobe (photoshop|illustrator|indesign|xd)", r"visual design", r"motion graphics", r"typography",
    ],
    "sales": [
        r"\bsales\b", r"lead generation", r"cold calling", r"account executive", r"quota", r"pipeline management",
        r"b2b sales", r"b2c sales", r"sales forecast", r"account management",
    ],
    "education": [
        r"curriculum", r"lesson plan", r"classroom management", r"instructional design", r"\bteach(er|ing)\b",
        r"student assessment", r"e-learning", r"learning management system",
    ],
    "customer_service": [
        r"customer service", r"customer support", r"help desk", r"\bzendesk\b", r"client onboarding",
        r"guest relations", r"front desk", r"retail operations", r"point of sale",
    ],
}

PROFESSION_LABELS = {
    "software_engineering": "Software Engineering",
    "marketing": "Marketing",
    "accounting": "Accounting",
    "business_administration": "Business Administration",
    "data_science": "Data Science",
    "healthcare": "Healthcare",
    "human_resources": "Human Resources",
    "legal": "Legal",
    "design": "Design",
    "sales": "Sales",
    "education": "Education",
    "customer_service": "Customer Service",
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


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item.strip())
    return result


def _distribute_gaps(gaps: list[str]) -> list[list[str]]:
    """Splits the actual missing-skill list into up to 4 roughly-even, ordered
    buckets — one per roadmap stage. Never invents extra entries to pad a
    bucket out; a gap list shorter than 4 simply produces fewer non-empty
    buckets (the caller drops the empty ones), and a gap list longer than 4
    keeps every gap, just distributed as evenly as possible across the 4
    stage slots."""
    n = len(gaps)
    if n == 0:
        return [[], [], [], []]
    num_buckets = min(4, n)
    base, extra = divmod(n, num_buckets)
    buckets = []
    start = 0
    for i in range(num_buckets):
        size = base + (1 if i < extra else 0)
        buckets.append(gaps[start:start + size])
        start += size
    while len(buckets) < 4:
        buckets.append([])
    return buckets


_STAGE_DEFS = [
    ("Foundation", "high", "2-3 weeks"),
    ("Intermediate", "high", "3-5 weeks"),
    ("Advanced", "critical", "3-5 weeks"),
    ("Job Ready", "critical", "2-3 weeks"),
]


def _no_gaps_topic(category_label: str, has_analysis: bool) -> dict:
    """Returned instead of any fixed skill content when there's nothing real
    to build a roadmap from — either the candidate's resume already covers
    everything the job description asks for, or there's no resume/job
    description pairing yet to compute gaps from at all. Either way, this is
    an honest status statement grounded in the actual match result, not a
    fabricated skill or generic filler topic."""
    if has_analysis:
        why = (
            f"Your resume already covers the skills your target job description asks for — there's no "
            f"critical gap identified for this {category_label.lower()} role right now."
        )
        objectives = [
            "Confirm your strongest matched skills are clearly showcased on your resume and portfolio.",
            "Prepare to discuss your matched skills confidently in an interview.",
        ]
    else:
        why = (
            "No job description has been analyzed against your resume yet, so no specific skill gaps have "
            "been identified. Save a resume and a target job description together to get a roadmap built "
            "from your actual missing skills."
        )
        objectives = [
            "Upload a resume and a target job description, then save an analysis.",
            "Revisit this roadmap once a skill-gap comparison is available.",
        ]
    return {
        "key": "no-gaps-identified",
        "title": "No critical skill gaps identified",
        "category": category_label,
        "why_it_matters": why,
        "learning_objectives": objectives,
        "resources": [],
        "projects": [],
        "exercises": [],
        "estimated_hours": 0,
        "priority": "medium",
    }


def build_roadmap(
    missing_skills: list[str], resume_skills: list[str],
    target_role: str | None = None, industry: str | None = None, resume_text: str = "",
) -> dict:
    """Builds every stage entirely from the caller's actual missing_skills —
    the real gaps identified by comparing the candidate's resume against
    their target job description (see matching_engine.calculate_skill_match).
    No stage is ever filled from a fixed, pre-written topic list: profession
    detection only decides how topics are labeled/grouped, never which
    topics appear. Two callers with different missing_skills always get
    different roadmap content, even within the same detected profession."""
    category = detect_profession_category(target_role, industry, resume_skills, missing_skills, resume_text)
    category_label = PROFESSION_LABELS.get(category, PROFESSION_LABELS["general"])
    skill_category_label = f"{category_label} Skills"

    gaps = _dedupe_preserve_order([s for s in (missing_skills or []) if s])

    if not gaps:
        has_analysis = bool(resume_skills) or bool((resume_text or "").strip())
        stages = [{
            "stage": "Job Ready",
            "description": "Status of your skill gaps against your target role.",
            "estimated_duration": "N/A",
            "milestone": "You're ready to apply, or ready to get a personalized roadmap once an analysis exists.",
            "topics": [_no_gaps_topic(category_label, has_analysis)],
        }]
        return {
            "stages": _add_depth_fields(stages),
            "detected_profession": target_role or category_label,
            "detected_industry": industry or "",
        }

    buckets = _distribute_gaps(gaps)
    stages = []
    for (stage_name, priority, duration), bucket_gaps in zip(_STAGE_DEFS, buckets):
        if not bucket_gaps:
            continue
        stages.append({
            "stage": stage_name,
            "description": f"Closes these specific skill gaps identified against your target {category_label.lower()} role.",
            "estimated_duration": duration,
            "milestone": f"You've closed these gaps ({', '.join(bucket_gaps)}) and can speak to them credibly in an interview.",
            "topics": [_skill_topic(skill, priority, skill_category_label) for skill in bucket_gaps],
        })

    return {
        "stages": _add_depth_fields(stages),
        "detected_profession": target_role or category_label,
        "detected_industry": industry or "",
    }
