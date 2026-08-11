"""One-off, idempotent seed for the four starter subscription plans (Free,
Basic, Premium, Enterprise) so the admin panel isn't an empty state on first
run. Every value here is editable afterward from Admin > Subscriptions > Plans
— this just gives reasonable defaults. Safe to re-run: skips any plan whose
slug already exists.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models.subscription_models import Plan, PlanLimit
from app.services.stripe_client import sync_plan_to_stripe

PLANS = [
    {
        "name": "Free",
        "slug": "free",
        "description": "Get started with the essentials.",
        "monthly_price_cents": 0,
        "yearly_price_cents": 0,
        "display_order": 0,
        "limits": {
            "resume_analysis": (1, 5),
            "ai_resume_builder": (1, 2),
            "interview_practice": (1, 3),
            "skill_assessment": (1, 3),
            "learning_roadmap": (1, 1),
            "documents": (1, 3),
            "github_analysis": (2, 10),
            "ai_chat": (5, 50),
        },
    },
    {
        "name": "Basic",
        "slug": "basic",
        "description": "For active job seekers who want more room to practice.",
        "monthly_price_cents": 999,
        "yearly_price_cents": 9999,
        "display_order": 1,
        "limits": {
            "resume_analysis": (5, 50),
            "ai_resume_builder": (3, 20),
            "interview_practice": (3, 20),
            "skill_assessment": (3, 20),
            "learning_roadmap": (1, 5),
            "documents": (2, 20),
            "github_analysis": (10, 100),
            "ai_chat": (30, 300),
        },
    },
    {
        "name": "Premium",
        "slug": "premium",
        "description": "Full-speed job search with generous AI usage.",
        "monthly_price_cents": 1999,
        "yearly_price_cents": 19999,
        "display_order": 2,
        "limits": {
            "resume_analysis": (15, 200),
            "ai_resume_builder": (10, 100),
            "interview_practice": (10, 100),
            "skill_assessment": (10, 100),
            "learning_roadmap": (5, 20),
            "documents": (10, 100),
            "github_analysis": (30, 500),
            "ai_chat": (100, 1500),
        },
    },
    {
        "name": "Enterprise",
        "slug": "enterprise",
        "description": "Unlimited usage for teams and organizations.",
        "monthly_price_cents": 4999,
        "yearly_price_cents": 49999,
        "display_order": 3,
        "limits": {
            "resume_analysis": (None, None),
            "ai_resume_builder": (None, None),
            "interview_practice": (None, None),
            "skill_assessment": (None, None),
            "learning_roadmap": (None, None),
            "documents": (None, None),
            "github_analysis": (None, None),
            "ai_chat": (None, None),
        },
    },
]


def run_seed():
    db = SessionLocal()
    try:
        for plan_data in PLANS:
            existing = db.query(Plan).filter(Plan.slug == plan_data["slug"]).first()
            if existing:
                print(f"Skipping '{plan_data['slug']}' — already exists.")
                continue

            plan = Plan(
                name=plan_data["name"],
                slug=plan_data["slug"],
                description=plan_data["description"],
                monthly_price_cents=plan_data["monthly_price_cents"],
                yearly_price_cents=plan_data["yearly_price_cents"],
                display_order=plan_data["display_order"],
            )
            sync_plan_to_stripe(plan)
            db.add(plan)
            db.flush()

            for feature_key, (daily_limit, monthly_limit) in plan_data["limits"].items():
                db.add(PlanLimit(plan_id=plan.id, feature_key=feature_key, daily_limit=daily_limit, monthly_limit=monthly_limit))

            db.commit()
            print(f"Created plan '{plan_data['slug']}'.")
    finally:
        db.close()

    print("Seed complete.")


if __name__ == "__main__":
    run_seed()
