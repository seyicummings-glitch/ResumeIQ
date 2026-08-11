"""
Rule-based learning roadmap builder — the no-AI fallback for
app/services/learning_roadmap_ai.py. No machine learning here: resources,
providers, and stage groupings are selected deterministically from fixed
lookup tables keyed by regex/keyword matches against the missing skill name.
Mirrors the style of matching_engine.py: pure functions, no FastAPI/SQLAlchemy
imports.

Produces the same {"stages": [...]} shape as the AI path (4 fixed stages —
Foundation, Intermediate, Advanced, Job Ready — each with topics carrying
title/why_it_matters/learning_objectives/resources/projects/exercises/
estimated_hours/priority) so the route layer and frontend don't need to
special-case which path generated the roadmap.
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
    if re.search(r"cka|cks|aws|gcp|azure|terraform associate", skill_lower):
        return "Cert"
    return "Course"


def get_provider(skill: str) -> str:
    for pattern, provider in _PROVIDER_TABLE:
        if pattern.search(skill or ""):
            return provider
    return "Multiple providers"


def _skill_topic(skill: str, priority: str) -> dict:
    hours = {"critical": 30, "high": 15, "medium": 8}[priority]
    return {
        "key": f"skill-{skill.lower().replace(' ', '-')}",
        "title": skill,
        "why_it_matters": f"Identified as a gap against the target role's requirements — closing it directly improves job readiness for this position.",
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


_FOUNDATION_TOPICS = [
    {
        "key": "foundation-git",
        "title": "Version control with Git",
        "why_it_matters": "Every professional engineering team collaborates through Git — it's assumed baseline knowledge in any technical interview.",
        "learning_objectives": ["Create branches, resolve merge conflicts, and write clear commit history.", "Use pull requests as part of a real code review workflow."],
        "resources": [
            {"name": "Pro Git (git-scm.com/book) — free", "type": "Free", "provider": "Git"},
            {"name": "Learn Git Branching (learngitbranching.js.org) — free", "type": "Free", "provider": "Community"},
        ],
        "projects": ["Contribute a small fix to an open-source repo via a pull request."],
        "exercises": ["Practice rebasing and resolving a merge conflict on a throwaway repo."],
        "estimated_hours": 6,
        "priority": "high",
    },
    {
        "key": "foundation-clean-code",
        "title": "Writing clean, testable code",
        "why_it_matters": "Code quality and testability are what separates a junior submission from a hire-ready one in technical screens.",
        "learning_objectives": ["Write functions with single responsibility and clear naming.", "Write unit tests that actually catch regressions."],
        "resources": [
            {"name": "Clean Code by Robert C. Martin", "type": "Book", "provider": "Prentice Hall"},
            {"name": "Testing your language's standard test framework — official docs", "type": "Docs", "provider": "Official docs"},
        ],
        "projects": ["Refactor an old personal project with a real test suite."],
        "exercises": ["Practice test-driven development on a small kata."],
        "estimated_hours": 10,
        "priority": "high",
    },
    {
        "key": "foundation-debugging",
        "title": "Debugging & problem-solving fundamentals",
        "why_it_matters": "Interviewers explicitly test how you reason under uncertainty — this is a core, role-agnostic hiring signal.",
        "learning_objectives": ["Use a debugger instead of print statements for non-trivial bugs.", "Systematically narrow down the root cause of a failure."],
        "resources": [
            {"name": "Your language/runtime's official debugger docs", "type": "Docs", "provider": "Official docs"},
            {"name": "Grokking Algorithms by Aditya Bhargava", "type": "Book", "provider": "Manning"},
        ],
        "projects": ["Deliberately break a project and practice root-causing it methodically."],
        "exercises": ["Solve 3-5 debugging-focused coding challenges."],
        "estimated_hours": 8,
        "priority": "medium",
    },
    {
        "key": "foundation-cs-fundamentals",
        "title": "Core data structures & algorithms",
        "why_it_matters": "Nearly every technical interview, regardless of role, still probes fundamental CS reasoning.",
        "learning_objectives": ["Explain time/space complexity of common operations.", "Implement and reason about arrays, hash maps, trees, and graphs."],
        "resources": [
            {"name": "Grokking Algorithms by Aditya Bhargava", "type": "Book", "provider": "Manning"},
            {"name": "NeetCode 150 (neetcode.io) — free", "type": "Free", "provider": "NeetCode"},
        ],
        "projects": ["Implement a small data structure (e.g. LRU cache) from scratch."],
        "exercises": ["Solve 10 easy/medium data structure problems."],
        "estimated_hours": 20,
        "priority": "high",
    },
]

_JOB_READY_TOPICS = [
    {
        "key": "job-ready-system-design",
        "title": "System design & architecture fundamentals",
        "why_it_matters": "Job-ready candidates can reason about trade-offs at a system level, not just write working code.",
        "learning_objectives": ["Design a system given rough requirements and articulate trade-offs.", "Reason about scaling, caching, and data consistency at a high level."],
        "resources": [
            {"name": "System Design Primer (github.com/donnemartin/system-design-primer) — free", "type": "Free", "provider": "Community"},
            {"name": "Grokking the System Design Interview", "type": "Course", "provider": "Educative"},
        ],
        "projects": ["Write a design doc for a system relevant to your target role."],
        "exercises": ["Practice 2-3 mock system design prompts out loud or in writing."],
        "estimated_hours": 15,
        "priority": "high",
    },
    {
        "key": "job-ready-portfolio",
        "title": "Portfolio & project storytelling",
        "why_it_matters": "Hiring managers screen on demonstrated, explainable work — not just a skills list.",
        "learning_objectives": ["Present a project's impact, trade-offs, and your specific contributions clearly.", "Curate 2-3 portfolio projects that map directly to the target role."],
        "resources": [
            {"name": "Your target companies' engineering blogs — free", "type": "Free", "provider": "Various"},
        ],
        "projects": ["Write a case-study README for your strongest project."],
        "exercises": ["Practice a 2-minute verbal walkthrough of your best project."],
        "estimated_hours": 6,
        "priority": "medium",
    },
    {
        "key": "job-ready-interview-prep",
        "title": "Behavioral interview readiness",
        "why_it_matters": "Behavioral rounds are a real, often deciding part of the hiring process — preparation compounds confidence.",
        "learning_objectives": ["Structure answers using a framework like STAR.", "Have 4-5 concrete stories ready covering conflict, failure, ownership, and impact."],
        "resources": [
            {"name": "Cracking the PM/Coding Interview behavioral chapters", "type": "Book", "provider": "CareerCup"},
        ],
        "projects": ["Write out and rehearse 5 STAR-format stories from your own experience."],
        "exercises": ["Run a mock behavioral interview with a friend or record yourself."],
        "estimated_hours": 6,
        "priority": "high",
    },
    {
        "key": "job-ready-mock-interviews",
        "title": "Mock interviews & feedback loops",
        "why_it_matters": "Interview performance is a skill in itself — realistic practice under pressure closes the gap between knowing and performing.",
        "learning_objectives": ["Complete a mock interview and identify specific weak points.", "Iterate on weak areas with targeted practice, not general review."],
        "resources": [
            {"name": "This platform's AI Interview Practice", "type": "Free", "provider": "ResumeIQ"},
        ],
        "projects": ["Complete at least 2 full mock interviews and act on the feedback."],
        "exercises": ["Time-box and complete one technical mock interview per week."],
        "estimated_hours": 4,
        "priority": "critical",
    },
]


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
    learning_roadmap_ai.py's ROADMAP_SCHEMA) without hand-authoring 16 topics' worth of it.
    Builds new dicts rather than mutating in place — _FOUNDATION_TOPICS/_JOB_READY_TOPICS are
    shared module-level lists reused across every call/request, so mutating their dicts in
    place would leak state between unrelated roadmaps."""
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


def build_roadmap(missing_skills: list[str], resume_skills: list[str]) -> dict:
    """Deterministic 4-stage roadmap: Foundation and Job Ready are evergreen,
    role-agnostic stages; Intermediate and Advanced are built from the
    identified skill gaps (first half = core/Intermediate, second half =
    differentiating/Advanced), tagged with a priority for the UI."""
    gaps = [s for s in (missing_skills or []) if s]
    midpoint = math.ceil(len(gaps) / 2)
    intermediate_gaps = gaps[:midpoint]
    advanced_gaps = gaps[midpoint:]

    stages = [
        {
            "stage": "Foundation",
            "description": "Core fundamentals expected of any professional in this field, independent of the specific tech stack.",
            "estimated_duration": "2-3 weeks",
            "milestone": "You can confidently work in a real codebase: version control, clean code, debugging, and core CS fundamentals.",
            "topics": _FOUNDATION_TOPICS,
        },
        {
            "stage": "Intermediate",
            "description": "The core, everyday skills expected for the target role.",
            "estimated_duration": "3-5 weeks",
            "milestone": "You can independently build a working feature end-to-end using the role's core stack.",
            "topics": [_skill_topic(skill, "high") for skill in intermediate_gaps] or [_skill_topic(skill, "medium") for skill in resume_skills[:2]],
        },
        {
            "stage": "Advanced",
            "description": "Specialized, differentiating skills that separate a strong candidate from an average one for this role.",
            "estimated_duration": "3-5 weeks",
            "milestone": "You've closed the identified skill gaps and can speak to them credibly in an interview.",
            "topics": [_skill_topic(skill, "critical") for skill in advanced_gaps] or [_skill_topic(skill, "medium") for skill in resume_skills[2:4]],
        },
        {
            "stage": "Job Ready",
            "description": "Interview readiness, portfolio polish, and system-level thinking — the final stretch before applying.",
            "estimated_duration": "2-3 weeks",
            "milestone": "You're ready to apply and interview for the target role with confidence.",
            "topics": _JOB_READY_TOPICS,
        },
    ]

    return {"stages": _add_depth_fields(stages)}
