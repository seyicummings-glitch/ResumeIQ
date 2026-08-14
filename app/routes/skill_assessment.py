import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import JobDescription, Resume, User
from app.models.skill_assessment_models import SkillAssessmentAttempt, SkillAssessmentSession, SkillQuestion
from app.security import get_current_user, get_session_id_from_request
from app.services.analysis_store import get_latest_analysis
from app.services.resume_structurer import extract_skills_list
from app.services.platform_settings import is_ai_enabled
from app.services.learning_roadmap import detect_profession_category
from app.services.analytics import track_event, EVENT_TYPES, FEATURE_SKILL_ASSESSMENT
from app.services.feature_gate import check_and_consume, FeatureAccessDenied
from app.services.skill_assessment import (
    DIFFICULTY_WEIGHT,
    MAX_TOTAL_COUNT,
    MIN_TOTAL_COUNT,
    build_assessment,
    category_breakdown,
    distribute_fallback_counts,
    match_categories,
    overall_score,
    pick_soft_scenarios,
    score_soft_fallback,
    score_technical,
)
from app.services.skill_assessment_ai import DEFAULT_TOTAL_COUNT, generate_assessment_questions, grade_assessment_answers

router = APIRouter(prefix="/skill-assessment", tags=["Skill Assessment"])

# "technical" and "problem_solving" roll up into the headline technical_score;
# "scenario" and "behavioral" roll up into the headline soft_score. Applies to
# both AI-generated and fallback question sets so the two headline scores mean
# the same thing regardless of which path built the assessment.
HARD_TYPES = {"technical", "problem_solving"}
SOFT_TYPES = {"scenario", "behavioral"}

QUESTIONS_FIXTURE_PATH = Path(__file__).resolve().parent.parent / "data" / "skill_questions.json"

with open(QUESTIONS_FIXTURE_PATH, "r", encoding="utf-8") as f:
    QUESTION_FIXTURES: list[dict] = json.load(f)

RECENT_SESSIONS_TO_AVOID = 3


def _question_to_dict(question: SkillQuestion) -> dict:
    return {
        "id": question.id,
        "category_key": question.category_key,
        "category_label": question.category_label,
        "difficulty": question.difficulty,
        "question": question.question,
        "options": question.options,
        "correct_index": question.correct_index,
        "explanation": question.explanation,
        "tip": question.tip,
    }


def _ensure_questions_seeded(db: Session) -> None:
    if db.query(SkillQuestion).count() == 0:
        for fixture in QUESTION_FIXTURES:
            db.add(SkillQuestion(**fixture))
        db.commit()


def _recent_sessions(db: Session, user_id: int) -> list[SkillAssessmentSession]:
    return (
        db.query(SkillAssessmentSession)
        .filter(SkillAssessmentSession.user_id == user_id)
        .order_by(SkillAssessmentSession.created_at.desc())
        .limit(RECENT_SESSIONS_TO_AVOID)
        .all()
    )


def _build_fallback_question_set(
    db: Session,
    combined_skills: list[str],
    recent: list[SkillAssessmentSession],
    total_count: int,
    profession_category: str | None = None,
) -> dict:
    _ensure_questions_seeded(db)
    technical_count, soft_count = distribute_fallback_counts(total_count)

    recent_fallback = [s for s in recent if s.source == "fallback"]
    recent_technical_ids = [
        q["id"] for s in recent_fallback for q in s.questions_json if "scenario_id" not in q
    ]
    # The soft-scenario pool is small (8 total), so only avoid the single most
    # recent attempt — looking back further would exhaust the whole pool
    # after two restarts and force reuse anyway.
    recent_soft_ids = [
        q["scenario_id"] for q in (recent_fallback[0].questions_json if recent_fallback else []) if "scenario_id" in q
    ]

    all_questions = [_question_to_dict(q) for q in db.query(SkillQuestion).all()]
    technical = build_assessment(
        all_questions, combined_skills, count=technical_count, exclude_ids=recent_technical_ids,
        profession_category=profession_category,
    )
    # A confidently non-technical profession with no matched skill category can come back
    # short here (see build_assessment's profession gating in app/services/skill_assessment.py)
    # rather than ever backfilling with the bank's software-engineering questions — make up
    # the difference with extra soft-skill scenarios so the total still matches total_count.
    soft = pick_soft_scenarios(count=soft_count + (technical_count - len(technical)), exclude_ids=recent_soft_ids)

    questions = [
        {
            "id": q["id"],
            "type": "technical",
            "input_type": "multiple_choice",
            "category": q["category_label"],
            "category_key": q["category_key"],
            "difficulty": q["difficulty"],
            "question": q["question"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "explanation": q["explanation"],
            "tip": q["tip"],
        }
        for q in technical
    ] + [
        {
            "id": 1000 + s["id"],
            "type": s["type"],
            "input_type": "text",
            "category": s["category"],
            "question": s["scenario"],
            "keywords": s["keywords"],
            "scenario_id": s["id"],
        }
        for s in soft
    ]

    return {"source": "fallback", "questions": questions}


def _build_ai_question_set(
    resume,
    target_role: str,
    industry: str,
    experience_level: str,
    missing_skills: list[str],
    jd_content: str,
    recent: list[SkillAssessmentSession],
    total_count: int,
) -> dict | None:
    recent_question_texts = [q["question"] for s in recent for q in s.questions_json]
    resume_skills = extract_skills_list(resume.skills or "") if resume else []
    resume_text = resume.raw_text if resume else ""

    generated = generate_assessment_questions(
        target_role=target_role,
        industry=industry,
        experience_level=experience_level,
        resume_text=resume_text or "",
        resume_skills=resume_skills,
        missing_skills=missing_skills,
        jd_content=jd_content,
        recent_questions=recent_question_texts,
        total_count=total_count,
    )
    if not generated:
        return None

    questions = []
    next_id = 1
    for type_key, source_key in [
        ("technical", "technical_questions"),
        ("scenario", "scenario_questions"),
        ("problem_solving", "problem_solving_questions"),
        ("behavioral", "behavioral_questions"),
    ]:
        for q in generated[source_key]:
            questions.append({
                "id": next_id,
                "type": type_key,
                "input_type": "text",
                "category": q["category"],
                "difficulty": q.get("difficulty"),
                "question": q["question"],
                "expected_answer_points": q["expected_answer_points"],
            })
            next_id += 1

    return {"source": "ai", "questions": questions}


def _public_question(q: dict) -> dict:
    """Strips grading-only fields (correct_index for fallback MC would give the
    answer away pre-submission for AI mode; expected_answer_points is the
    hidden AI rubric) before a question set is sent to the client."""
    hidden_fields = {"expected_answer_points"}
    return {k: v for k, v in q.items() if k not in hidden_fields}


@router.get("/build")
def build_skill_assessment(
    question_count: int = Query(DEFAULT_TOTAL_COUNT, ge=MIN_TOTAL_COUNT, le=MAX_TOTAL_COUNT),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    try:
        analysis = get_latest_analysis(db, current_user.id)
        if not current_user.target_role and not analysis:
            return {
                "session_id": None,
                "source": None,
                "questions": [],
                "detected_categories": [],
                "has_context": False,
            }

        try:
            check_and_consume(db, current_user, "skill_assessment")
        except FeatureAccessDenied as exc:
            raise HTTPException(status_code=402, detail=exc.payload)

        resume = None
        resume_skills: list[str] = []
        missing_skills: list[str] = []
        jd_title = ""
        jd_content = ""
        if analysis:
            resume = db.query(Resume).filter(Resume.id == analysis.resume_id).first()
            resume_skills = extract_skills_list(resume.skills or "") if resume else []
            missing_skills = (analysis.result_json or {}).get("skill_match", {}).get("missing_skills", []) or []
            jd = db.query(JobDescription).filter(JobDescription.id == analysis.job_description_id).first()
            jd_title = jd.title if jd and jd.title else ""
            jd_content = jd.content if jd else ""

        combined_skills = list(resume_skills) + list(missing_skills)
        recent = _recent_sessions(db, current_user.id)
        profession_category = detect_profession_category(
            target_role=current_user.target_role, industry=current_user.industry,
            resume_skills=resume_skills, missing_skills=missing_skills,
            resume_text=resume.raw_text if resume else "",
        )

        question_set = None
        if is_ai_enabled(db):
            question_set = _build_ai_question_set(
                resume,
                current_user.target_role or "",
                current_user.industry or "",
                current_user.experience_level or "",
                missing_skills,
                jd_content,
                recent,
                question_count,
            )
        if question_set is None:
            question_set = _build_fallback_question_set(db, combined_skills, recent, question_count, profession_category)

        session = SkillAssessmentSession(
            user_id=current_user.id,
            source=question_set["source"],
            questions_json=question_set["questions"],
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        track_event(
            db, EVENT_TYPES["ASSESSMENT_STARTED"], FEATURE_SKILL_ASSESSMENT, user_id=current_user.id,
            metadata={"session_id": session.id, "source": session.source, "question_count": len(question_set["questions"])},
            request=request, session_id=get_session_id_from_request(request),
        )

        return {
            "session_id": session.id,
            "source": question_set["source"],
            "questions": [_public_question(q) for q in question_set["questions"]],
            "detected_categories": match_categories(combined_skills),
            "has_context": True,
            "jd_title": jd_title or current_user.target_role,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building assessment: {str(e)}")


class AnswerInput(BaseModel):
    question_id: int
    answer_text: str | None = None
    answer_index: int | None = None


class AssessmentSubmitInput(BaseModel):
    session_id: int
    answers: list[AnswerInput]


def _heuristic_grade(question: dict, answer_text: str) -> dict:
    """Last-resort grading for the rare case a session was generated by AI but
    the grading call itself then fails — a keyword-overlap check against the
    rubric so a blank/off-topic answer still can't score well, without
    claiming to be real AI feedback."""
    rubric_words = {w.strip(".,;:").lower() for w in question.get("expected_answer_points", "").split() if len(w) > 4}
    answer_words = {w.strip(".,;:").lower() for w in (answer_text or "").split()}
    overlap = len(rubric_words & answer_words)
    word_count = len(answer_text.split()) if answer_text else 0

    if word_count < 10:
        score = 0
    else:
        score = min(65, 15 + overlap * 12)

    return {
        "question_id": question["id"],
        "score": score,
        "is_correct": score >= 70,
        "explanation": "AI grading was temporarily unavailable, so this answer was scored with a basic keyword check instead of full review.",
        "correct_answer_or_improvement": question.get("expected_answer_points", ""),
    }


@router.post("/submit")
def submit_skill_assessment(
    data: AssessmentSubmitInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    try:
        session = db.query(SkillAssessmentSession).filter(
            SkillAssessmentSession.id == data.session_id, SkillAssessmentSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Assessment session not found or already submitted.")

        submitted_by_id = {a.question_id: a for a in data.answers}
        questions = session.questions_json
        technical_questions = [q for q in questions if q["type"] in HARD_TYPES]
        soft_questions = [q for q in questions if q["type"] in SOFT_TYPES]

        question_feedback: list[dict] = []

        if session.source == "ai":
            items = []
            for q in questions:
                submitted = submitted_by_id.get(q["id"])
                answer_text = submitted.answer_text if submitted else None
                items.append({
                    "id": q["id"],
                    "type": q["type"],
                    "question": q["question"],
                    "expected_answer_points": q["expected_answer_points"],
                    "answer": answer_text,
                })

            graded = grade_assessment_answers(items, ai_enabled=is_ai_enabled(db))
            results_by_id = {}
            if graded:
                results_by_id = {r["question_id"]: r for r in graded}
            else:
                for item in items:
                    result = _heuristic_grade(
                        next(q for q in questions if q["id"] == item["id"]), item["answer"]
                    )
                    results_by_id[item["id"]] = result

            for q in questions:
                result = results_by_id[q["id"]]
                submitted = submitted_by_id.get(q["id"])
                question_feedback.append({
                    "question_id": q["id"],
                    "type": q["type"],
                    "category": q["category"],
                    "difficulty": q.get("difficulty"),
                    "question": q["question"],
                    "answer": submitted.answer_text if submitted else None,
                    "score": result["score"],
                    "is_correct": result["is_correct"],
                    "explanation": result["explanation"],
                    "correct_answer_or_improvement": result["correct_answer_or_improvement"],
                })

            technical_feedback = [f for f in question_feedback if f["type"] in HARD_TYPES]
            soft_feedback = [f for f in question_feedback if f["type"] in SOFT_TYPES]

            weighted_total = sum(f["score"] * DIFFICULTY_WEIGHT.get(f["difficulty"], 2) for f in technical_feedback)
            weight_sum = sum(DIFFICULTY_WEIGHT.get(f["difficulty"], 2) for f in technical_feedback)
            technical_score = round(weighted_total / weight_sum) if weight_sum else 0
            soft_score = round(sum(f["score"] for f in soft_feedback) / len(soft_feedback)) if soft_feedback else 0
            correct_count = sum(1 for f in technical_feedback if f["is_correct"])

            categories: dict[str, list[int]] = {}
            for f in technical_feedback:
                categories.setdefault(f["category"], []).append(f["score"])
            breakdown = [
                {"category_key": name, "category_label": name, "pct": round(sum(scores) / len(scores))}
                for name, scores in categories.items()
            ]
            breakdown.sort(key=lambda item: item["pct"], reverse=True)

        else:
            answers_by_id = {a.question_id: a.answer_index for a in data.answers if a.answer_index is not None}
            technical_result = score_technical(technical_questions, answers_by_id)
            technical_score = technical_result["technical_score"]
            correct_count = technical_result["correct_count"]
            breakdown = category_breakdown(technical_questions, answers_by_id)

            soft_scores = []
            for q in soft_questions:
                submitted = submitted_by_id.get(q["id"])
                answer_text = submitted.answer_text if submitted else ""
                scenario = {"keywords": q.get("keywords", [])}
                score = score_soft_fallback(scenario, answer_text)
                soft_scores.append(score)
                question_feedback.append({
                    "question_id": q["id"],
                    "type": q["type"],
                    "category": q["category"],
                    "question": q["question"],
                    "answer": answer_text,
                    "score": score,
                    "is_correct": score >= 70,
                    "explanation": "Rule-based scoring based on relevant keywords and answer depth — enable AI grading for detailed, content-aware feedback.",
                    "correct_answer_or_improvement": "AI-generated improvement suggestions aren't available in fallback mode.",
                })
            soft_score = round(sum(soft_scores) / len(soft_scores)) if soft_scores else 0

            for q in technical_questions:
                selected = answers_by_id.get(q["id"])
                is_correct = selected is not None and selected == q["correct_index"]
                question_feedback.append({
                    "question_id": q["id"],
                    "type": "technical",
                    "category": q["category"],
                    "difficulty": q["difficulty"],
                    "question": q["question"],
                    "answer": q["options"][selected] if selected is not None and 0 <= selected < len(q["options"]) else None,
                    "score": 100 if is_correct else 0,
                    "is_correct": is_correct,
                    "explanation": q["explanation"],
                    "correct_answer_or_improvement": q["options"][q["correct_index"]],
                })

        final_score = overall_score(technical_score, soft_score)

        attempt = SkillAssessmentAttempt(
            user_id=current_user.id,
            session_id=session.id,
            source=session.source,
            technical_score=technical_score,
            soft_score=soft_score,
            overall_score=final_score,
            category_breakdown=breakdown,
            question_feedback=question_feedback,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        session_id = get_session_id_from_request(request)
        for feedback_item in question_feedback:
            track_event(
                db, EVENT_TYPES["QUESTION_ANSWERED"], FEATURE_SKILL_ASSESSMENT, user_id=current_user.id,
                metadata={
                    "attempt_id": attempt.id, "question_id": feedback_item["question_id"],
                    "type": feedback_item["type"], "is_correct": feedback_item["is_correct"],
                },
                request=request, session_id=session_id,
            )
        attempt_metadata = {
            "attempt_id": attempt.id, "technical_score": technical_score,
            "soft_score": soft_score, "overall_score": final_score,
        }
        track_event(db, EVENT_TYPES["ASSESSMENT_COMPLETED"], FEATURE_SKILL_ASSESSMENT, user_id=current_user.id,
                    metadata=attempt_metadata, request=request, session_id=session_id)
        track_event(db, EVENT_TYPES["ASSESSMENT_SCORED"], FEATURE_SKILL_ASSESSMENT, user_id=current_user.id,
                    metadata=attempt_metadata, request=request, session_id=session_id)

        return {
            "technical_score": technical_score,
            "soft_score": soft_score,
            "overall_score": final_score,
            "correct_count": correct_count,
            "total": len(technical_questions),
            "category_breakdown": breakdown,
            "question_feedback": question_feedback,
            "source": session.source,
            "attempt_id": attempt.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting assessment: {str(e)}")


@router.get("/history")
def get_skill_assessment_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempts = (
        db.query(SkillAssessmentAttempt)
        .filter(SkillAssessmentAttempt.user_id == current_user.id)
        .order_by(SkillAssessmentAttempt.created_at.desc())
        .all()
    )
    return [
        {
            "id": attempt.id,
            "technical_score": attempt.technical_score,
            "soft_score": attempt.soft_score,
            "overall_score": attempt.overall_score,
            "category_breakdown": attempt.category_breakdown,
            "source": attempt.source,
            "created_at": attempt.created_at,
        }
        for attempt in attempts
    ]
