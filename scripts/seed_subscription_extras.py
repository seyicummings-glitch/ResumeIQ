"""One-off, idempotent seed for credit packages, so the admin panel and the
user-facing "Buy Credits" flow aren't an empty state on first run. Every
value here is editable afterward from Admin > Subscriptions > Credit
Packages. Safe to re-run: skips any package whose name already exists.

AiFeatureSetting and PaymentMethodConfig rows don't need a seed script —
they're lazily created with safe defaults the first time an admin opens the
relevant settings page (see app.services.subscription_admin's
get_or_seed_feature_settings / get_or_seed_payment_methods)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models.subscription_models import CreditPackage

PACKAGES = [
    {"name": "100 Credits", "credits": 100, "price_cents": 999, "display_order": 0},
    {"name": "500 Credits", "credits": 500, "price_cents": 3999, "display_order": 1},
    {"name": "1000 Credits", "credits": 1000, "price_cents": 6999, "display_order": 2},
]


def run_seed():
    db = SessionLocal()
    try:
        for package_data in PACKAGES:
            existing = db.query(CreditPackage).filter(CreditPackage.name == package_data["name"]).first()
            if existing:
                print(f"Skipping '{package_data['name']}' — already exists.")
                continue

            db.add(CreditPackage(**package_data))
            db.commit()
            print(f"Created credit package '{package_data['name']}'.")
    finally:
        db.close()

    print("Seed complete.")


if __name__ == "__main__":
    run_seed()
