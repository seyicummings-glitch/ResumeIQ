"""Payment provider abstraction for subscription/credit purchases.

*** TEST-MODE ONLY — no real payment provider is wired up yet. ***
process_payment() below simulates a successful charge deterministically. No
real money moves, and none ever could through this module as written: it
takes only (method, amount_cents, currency) — there is no parameter for a
card number, CVV, or expiry anywhere in its signature, so it is structurally
impossible for this code path to receive or store card data, satisfying the
"never store sensitive payment information" requirement by construction
rather than by discipline.

Going live with a real processor (Stripe/PayPal/a Bitcoin payment
processor/...) means replacing the body of process_payment() with a real
API call to that provider's server-side charge/checkout API and needs real
provider credentials the user must supply (the same prerequisite flagged for
the Stripe integration in app/services/stripe_client.py, which remains
unused for the same reason). Every call site in this codebase goes through
this one function, so that swap is a single-file change — nothing else
needs to know the difference.
"""
import uuid
from dataclasses import dataclass

SUPPORTED_METHODS = {"credit_card", "debit_card", "paypal", "bitcoin"}


@dataclass
class PaymentResult:
    status: str  # "succeeded" | "failed"
    external_reference: str
    message: str


def process_payment(method: str, amount_cents: int, currency: str = "usd") -> PaymentResult:
    """Simulates sending a charge to `method` for amount_cents/currency and
    getting a confirmation back. Always succeeds in this test-mode
    implementation (there's no real provider to reject the charge) unless
    the method itself isn't one this platform claims to support at all, or
    the amount is invalid — those are real, local validation failures, not
    simulated provider ones."""
    if method not in SUPPORTED_METHODS:
        return PaymentResult(status="failed", external_reference="", message=f"Unsupported payment method: {method}")
    if amount_cents <= 0:
        return PaymentResult(status="failed", external_reference="", message="Invalid charge amount.")

    reference = f"MOCK-TX-{uuid.uuid4().hex[:12].upper()}"
    return PaymentResult(status="succeeded", external_reference=reference, message="Payment processed (test mode).")
