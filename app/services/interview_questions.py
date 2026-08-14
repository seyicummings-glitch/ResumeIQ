"""
Rule-based interview question generator.

No machine learning or AI models are used here — every question set below is
selected deterministically from a fixed bank using regex/keyword matching
against the candidate's resume skills, the job description's missing skills,
and the job title. Mirrors the style of matching_engine.py: pure functions,
no FastAPI/SQLAlchemy imports.

The System Design and default Role-Specific content (below) is
software-engineering-specific and only served when
app.services.learning_roadmap.detect_profession_category resolves to
"software_engineering" for the given job title/skills — everything else
(BEHAVIORAL_BASE, the technical depth-check/gap questions) is written to be
profession-neutral so it's honestly reusable for any candidate.
"""
import re

from app.services.learning_roadmap import detect_profession_category

BEHAVIORAL_BASE = [
    {
        "id": 101,
        "category": "Behavioral",
        "difficulty": "Medium",
        "question": "Tell me about a time you had to deliver something important under significant constraints (time, resources, or unclear requirements). How did you manage the trade-offs between quality and the deadline?",
        "tip": "Use the STAR method: Situation, Task, Action, Result. Quantify the outcome where you can — a vague 'it went well' is weak; a specific, measurable result is strong.",
        "sample_answer": "At my last role, we had six weeks to deliver a critical piece of work before a client deadline. I scoped a tiered approach: the essential requirements first, done properly, then extras only if time allowed. I cut a few 'nice to have' items and documented the trade-offs for stakeholders up front. We delivered on schedule with no quality complaints — a real improvement over how the previous project had gone.",
        "relevance": "Tests decision-making under pressure — relevant to any role",
    },
    {
        "id": 102,
        "category": "Behavioral",
        "difficulty": "Easy",
        "question": "How do you stay current with new developments, tools, or best practices in your field, and how do you decide which ones are actually worth adopting into your regular work?",
        "tip": "They want intellectual curiosity balanced with pragmatism. Don't just list where you get information — explain your evaluation framework.",
        "sample_answer": "I follow a three-stage filter: (1) awareness — I track what's new through a few trusted publications and professional communities; (2) evaluation — I try it out in a low-stakes way first to understand the real trade-offs versus the hype; (3) real adoption — only after a clear fit for an actual problem, and a plan to back out if it doesn't work. That keeps me curious without being reckless.",
        "relevance": "Common culture-fit question about pragmatic adoption of new ideas",
    },
    {
        "id": 103,
        "category": "Behavioral",
        "difficulty": "Medium",
        "question": "Describe a time you disagreed with a decision made by your team or manager. How did you handle it?",
        "tip": "Show you can advocate for your view while respecting process. The best answers demonstrate both confidence in your reasoning and emotional intelligence.",
        "sample_answer": "My team was about to move forward with an approach I'd looked into and found had real downsides. I put together a short, clear comparison against the alternatives — cost, risk, long-term impact — and proposed a different option. My manager appreciated the structured argument even though we ultimately kept the original choice due to time constraints. I documented my concerns so we could revisit the decision later.",
        "relevance": "Tests maturity and ability to handle disagreement professionally",
    },
]

# --- Technical depth-check questions, keyed by a regex matched against a resume skill ---
_SKILL_DEPTH_QUESTIONS = [
    (
        re.compile(r"\breact(\.js)?\b", re.IGNORECASE),
        {
            "difficulty": "Medium",
            "question": "Your resume lists React. Walk me through how you'd diagnose a component that's re-rendering far more often than expected.",
            "tip": "Mention the React DevTools Profiler, memoization (useMemo/useCallback/React.memo), and checking for unstable props/context values — not just 'I'd add React.memo everywhere.'",
            "sample_answer": "I'd start with the React DevTools Profiler to see which components re-render and why. Common culprits are new object/array/function literals created inline as props, or a context value that changes reference every render. I'd stabilize those with useMemo/useCallback, then only reach for React.memo on expensive leaf components once the unstable-reference issue is actually fixed — memoizing without fixing the root cause just hides the problem.",
            "relevance": "Depth-check on a skill already listed on your resume: React",
        },
    ),
    (
        re.compile(r"\b(node(\.js)?|express(\.js)?)\b", re.IGNORECASE),
        {
            "difficulty": "Medium",
            "question": "Your resume lists Node/Express. How do you handle an unhandled promise rejection in a long-running Express service without crashing the whole process?",
            "tip": "They want to know you understand the event loop and process-level error handling, not just try/catch inside a single route.",
            "sample_answer": "Every route handler should either be wrapped so async errors are forwarded to Express's error middleware (e.g. a small asyncHandler wrapper) or use a framework that does this natively. At the process level, I register 'unhandledRejection' and 'uncaughtException' listeners that log the error, alert, and do a controlled shutdown behind a process manager rather than letting the process silently limp along in an inconsistent state.",
            "relevance": "Depth-check on a skill already listed on your resume: Node/Express",
        },
    ),
    (
        re.compile(r"\bpython\b", re.IGNORECASE),
        {
            "difficulty": "Medium",
            "question": "Your resume lists Python. Explain the GIL and how it affects the way you'd design a CPU-bound vs. an I/O-bound workload.",
            "tip": "Show you know when threading helps (I/O-bound) versus when you need multiprocessing or a different runtime (CPU-bound), not just a textbook definition of the GIL.",
            "sample_answer": "The Global Interpreter Lock means only one thread executes Python bytecode at a time in CPython. For I/O-bound work — network calls, file reads — threading still helps because the GIL is released during blocking I/O. For CPU-bound work, like heavy computation, I'd reach for multiprocessing (separate processes, separate GILs) or offload to a native extension/async C library rather than expecting threads to give a speedup.",
            "relevance": "Depth-check on a skill already listed on your resume: Python",
        },
    ),
]

# --- Technical questions for gap skills the JD requires but the resume lacks ---
_MISSING_SKILL_QUESTIONS = {
    re.compile(r"\bdocker\b", re.IGNORECASE): {
        "difficulty": "Medium",
        "question": "The job description requires Docker, which isn't on your current resume. What's your understanding of the difference between an image and a container, and how would you keep an image small in production?",
        "tip": "Honesty + a concrete learning plan beats pretending you know it. Show you understand the concepts even if you haven't shipped with it professionally.",
        "sample_answer": "An image is the immutable, layered filesystem + metadata; a container is a running instance of that image with its own writable layer. To keep images small I'd use a slim/alpine base, multi-stage builds so build tooling doesn't ship in the final image, and a .dockerignore to avoid copying unnecessary files. I'd get hands-on by containerizing a small personal project end-to-end before my start date.",
        "relevance": "'docker' is listed as a required skill you don't currently have",
    },
    re.compile(r"\bkubernetes\b|\bk8s\b", re.IGNORECASE): {
        "difficulty": "Hard",
        "question": "The job description requires Kubernetes, which isn't on your current resume. How would you approach ramping up on it given you already know Docker/containers?",
        "tip": "Bridge from what you already know (containers) to what's new (orchestration: scheduling, service discovery, self-healing). Mention a concrete learning plan.",
        "sample_answer": "I already understand containers, so the new surface area is orchestration: pods, deployments, services, and how the control plane keeps desired state. I'd start with a local cluster (kind or minikube), deploy a small multi-service app, and deliberately break things — kill a pod, scale a deployment — to build intuition for how Kubernetes self-heals. I'd expect to reach working proficiency in a few weeks of focused practice.",
        "relevance": "'kubernetes' is listed as a required skill you don't currently have",
    },
    re.compile(r"\btypescript\b", re.IGNORECASE): {
        "difficulty": "Easy",
        "question": "The job description requires TypeScript, which isn't on your current resume. How would you approach adopting it if your current codebase is plain JavaScript?",
        "tip": "Show a pragmatic incremental-adoption mindset — TypeScript doesn't require a big-bang rewrite.",
        "sample_answer": "TypeScript is a superset of JavaScript, so I'd enable it with allowJs and strict mode off initially, then convert files incrementally starting with the most-shared utility modules and type definitions for external data (API responses). I'd tighten strictness over time rather than trying to get full type coverage on day one. I've picked up statically-typed tooling before and expect to be productive within a couple of weeks.",
        "relevance": "'typescript' is listed as a required skill you don't currently have",
    },
}


def _generic_missing_skill_question(skill: str, question_id: int) -> dict:
    return {
        "id": question_id,
        "category": "Technical",
        "difficulty": "Medium",
        "question": f"The job description requires {skill}, which isn't on your current resume. How would you approach getting up to speed?",
        "tip": "Honesty + a concrete learning plan beats pretending you know it.",
        "sample_answer": f"I'd start with the official documentation to understand core concepts, then build a small project to get hands-on quickly. I've learned similar technologies this way before and find I can reach productive proficiency in 2-4 weeks with focused effort.",
        "relevance": f"'{skill}' is listed as a required skill you don't currently have",
    }


def build_technical_questions(missing_skills: list, resume_skills: list) -> list:
    """Up to 4 technical questions: one depth-check on an existing resume skill
    (stops scanning after the first match among the first 4 resume skills),
    plus up to 2 questions probing skills the JD requires that are missing
    from the resume."""
    questions = []
    next_id = 200

    for skill in (resume_skills or [])[:4]:
        matched = None
        for pattern, template in _SKILL_DEPTH_QUESTIONS:
            if pattern.search(skill):
                matched = template
                break
        if matched:
            questions.append({"id": next_id, "category": "Technical", **matched})
            next_id += 1
            break

    for skill in (missing_skills or [])[:2]:
        specific = None
        for pattern, template in _MISSING_SKILL_QUESTIONS.items():
            if pattern.search(skill):
                specific = template
                break
        if specific:
            questions.append({"id": next_id, "category": "Technical", **specific})
        else:
            questions.append(_generic_missing_skill_question(skill, next_id))
        next_id += 1

    return questions[:4]


def _resolve_profession_category(jd_title: str, profession_category: str | None) -> str:
    """Callers that already know the detected profession (build_interview_questions,
    which has resume_skills/missing_skills too) pass it in directly; standalone callers
    (including these functions' own unit tests) fall back to detecting from jd_title
    alone, which is enough to correctly resolve titles like "Backend Engineer"."""
    if profession_category is not None:
        return profession_category
    return detect_profession_category(target_role=jd_title, industry=None, resume_skills=[], missing_skills=[])


def build_system_design_questions(jd_title: str, profession_category: str | None = None) -> list:
    # System design (data modeling, scaling, exactly-once semantics) is a software-engineering-
    # specific interview format — never served for a detected profession that isn't technical.
    if _resolve_profession_category(jd_title, profession_category) != "software_engineering":
        return []

    questions = []
    title = (jd_title or "").lower()

    if re.search(r"payment|fintech|finance|transaction", title):
        questions.append(
            {
                "id": 301,
                "category": "System Design",
                "difficulty": "Hard",
                "question": "Design a payment processing system that must never double-charge a customer, even if the client retries a request after a timeout. How would you guarantee exactly-once semantics?",
                "tip": "The key ideas are idempotency keys, a durable request-state table, and (for multi-step transactions) the saga pattern with compensating actions. Don't just say 'use a database transaction' — the hard part is across service boundaries.",
                "sample_answer": "I'd require every payment request to carry a client-generated idempotency key, stored in a table with a unique constraint before any charge is attempted. If a duplicate key arrives, I return the original cached result instead of reprocessing. For a multi-step flow — reserve funds, capture, notify — I'd model it as a saga: each step is recorded with its own state transition, and if a later step fails, compensating actions (refund, release reservation) roll the earlier steps back. This gives exactly-once effect even though the underlying calls are at-least-once.",
                "relevance": "Payments/fintech job — exactly-once semantics and idempotency are core to the role",
            }
        )

    questions.append(
        {
            "id": 302,
            "category": "System Design",
            "difficulty": "Hard",
            "question": "Design a URL shortener like bit.ly. Cover the data model, how you'd generate short codes, and how you'd scale reads.",
            "tip": "Cover: data model (long_url, short_code, created_at, optional expiry/owner), short-code generation (base62 encoding of an auto-increment ID vs. random + collision check), and caching/read scaling since reads vastly outnumber writes.",
            "sample_answer": "Data model: a table keyed by short_code (indexed, unique) storing long_url, created_at, and optionally owner_id/expiry. For code generation I'd base62-encode an auto-incrementing ID (or a Snowflake-style distributed ID to avoid a single sequence bottleneck) rather than pure random strings, which need collision retries. Reads (redirects) vastly outnumber writes, so I'd put a cache — Redis or a CDN edge cache — in front of the redirect lookup, with the database as the source of truth and a short TTL or write-through invalidation on updates. I'd shard the DB by short_code hash if write volume ever became the bottleneck.",
            "relevance": "Classic system design question testing data modeling and read-scaling instincts",
        }
    )

    return questions


def _generic_role_question() -> dict:
    return {
        "id": 402,
        "category": "Role-Specific",
        "difficulty": "Medium",
        "question": "Tell me about how you take ownership of your work from start to finish — what does doing your job well look like day to day, and how do you make sure quality stays high?",
        "tip": "They want to see accountability beyond just completing a task — planning ahead, catching your own mistakes, and following through rather than considering it done the moment you hand it off.",
        "sample_answer": "Owning my work means I don't consider something finished until it's actually delivered correctly and the people it affects know what changed. I check my own work against what was asked before handing it off, flag risks early rather than letting them become surprises later, and follow up afterward to make sure it actually worked as intended in practice.",
        "relevance": "Tests ownership mindset and follow-through, relevant to any role",
    }


def build_role_questions(jd_title: str, profession_category: str | None = None) -> list:
    # The senior/on-call variants below are software-engineering-specific (code review,
    # production ownership) — any other detected profession gets a profession-neutral
    # ownership question instead, never these verbatim.
    if _resolve_profession_category(jd_title, profession_category) != "software_engineering":
        return [_generic_role_question()]

    title = (jd_title or "").lower()

    if re.search(r"senior|staff|lead|principal", title):
        return [
            {
                "id": 402,
                "category": "Role-Specific",
                "difficulty": "Hard",
                "question": "As a senior engineer, how do you approach mentoring less experienced teammates and raising the technical standards of a team through code review?",
                "tip": "Show a system, not just good intentions: how you give feedback, how you decide what's a blocking comment vs. a nit, and how you scale yourself beyond 1:1 mentoring.",
                "sample_answer": "In code review I distinguish blocking issues (correctness, security, maintainability) from stylistic nits, and I explain the 'why' behind a comment so it teaches, not just corrects. For mentoring, I pair on hard problems rather than just answering questions, and I push documentation and lightweight design docs so standards live in writing, not just in my head — that's what actually scales beyond one-on-one time.",
                "relevance": "Senior/lead-level role — expect questions on mentoring and technical leadership",
            }
        ]

    return [
        {
            "id": 402,
            "category": "Role-Specific",
            "difficulty": "Medium",
            "question": "Tell me about how you think about owning a service in production — what does 'on-call' mean to you and how do you keep reliability high?",
            "tip": "They want to see you think beyond 'write the code and ship it' — monitoring, alerting, runbooks, and postmortems are all fair game.",
            "sample_answer": "Owning a service means the responsibility doesn't end at merge — I make sure there's meaningful monitoring and alerting tied to user-facing symptoms (error rate, latency) rather than just infrastructure metrics, and a runbook so an on-call response doesn't depend on me personally being awake. After an incident I write a blameless postmortem focused on process and system gaps, not individual blame, so the same failure mode doesn't repeat.",
            "relevance": "Tests ownership mindset and operational maturity for individual-contributor roles",
        }
    ]


def build_interview_questions(missing_skills: list, resume_skills: list, jd_title: str) -> list:
    """Orchestrator: full personalized question set for a given analysis. Detects the
    profession once (from all available signal — title, resume skills, and gap skills)
    so the System Design / Role-Specific sections below are gated consistently rather
    than each re-guessing from jd_title alone."""
    category = detect_profession_category(
        target_role=jd_title, industry=None, resume_skills=resume_skills, missing_skills=missing_skills,
    )
    return (
        list(BEHAVIORAL_BASE)
        + build_technical_questions(missing_skills, resume_skills)
        + build_system_design_questions(jd_title, profession_category=category)
        + build_role_questions(jd_title, profession_category=category)
    )
