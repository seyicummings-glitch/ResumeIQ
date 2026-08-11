from unittest.mock import patch, Mock

from app.models.subscription_models import Plan
from app.services.stripe_client import is_stripe_configured, sync_plan_to_stripe


def test_is_stripe_configured_false_without_key(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert is_stripe_configured() is False


def test_is_stripe_configured_true_with_key(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    assert is_stripe_configured() is True


def test_sync_plan_to_stripe_noops_when_not_configured(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    plan = Plan(name="Free", slug="free", monthly_price_cents=0)

    with patch("app.services.stripe_client.stripe") as mock_stripe:
        sync_plan_to_stripe(plan)
        mock_stripe.Product.create.assert_not_called()

    assert plan.stripe_product_id is None


@patch("app.services.stripe_client.stripe")
def test_sync_plan_to_stripe_creates_product_and_prices(mock_stripe, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    plan = Plan(name="Basic", slug="basic", description="A basic plan.", monthly_price_cents=999, yearly_price_cents=9999, currency="usd")

    mock_stripe.Product.create.return_value = Mock(id="prod_123")
    mock_stripe.Price.create.side_effect = [Mock(id="price_monthly_1"), Mock(id="price_yearly_1")]

    sync_plan_to_stripe(plan)

    mock_stripe.Product.create.assert_called_once_with(name="Basic", description="A basic plan.")
    assert plan.stripe_product_id == "prod_123"
    assert plan.stripe_monthly_price_id == "price_monthly_1"
    assert plan.stripe_yearly_price_id == "price_yearly_1"
    assert mock_stripe.Price.create.call_count == 2
    mock_stripe.Price.modify.assert_not_called()  # nothing to archive on first sync


@patch("app.services.stripe_client.stripe")
def test_sync_plan_to_stripe_updates_product_and_archives_old_prices(mock_stripe, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    plan = Plan(
        name="Basic", slug="basic", monthly_price_cents=1499, yearly_price_cents=14999, currency="usd",
        stripe_product_id="prod_123", stripe_monthly_price_id="price_old_monthly", stripe_yearly_price_id="price_old_yearly",
    )

    mock_stripe.Price.create.side_effect = [Mock(id="price_new_monthly"), Mock(id="price_new_yearly")]

    sync_plan_to_stripe(plan)

    mock_stripe.Product.modify.assert_called_once_with("prod_123", name="Basic", description="")
    mock_stripe.Product.create.assert_not_called()
    assert plan.stripe_monthly_price_id == "price_new_monthly"
    assert plan.stripe_yearly_price_id == "price_new_yearly"
    mock_stripe.Price.modify.assert_any_call("price_old_monthly", active=False)
    mock_stripe.Price.modify.assert_any_call("price_old_yearly", active=False)


@patch("app.services.stripe_client.stripe")
def test_sync_plan_to_stripe_clears_yearly_price_when_removed(mock_stripe, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    plan = Plan(
        name="Basic", slug="basic", monthly_price_cents=999, yearly_price_cents=None, currency="usd",
        stripe_product_id="prod_123", stripe_monthly_price_id="price_old_monthly", stripe_yearly_price_id="price_old_yearly",
    )

    mock_stripe.Price.create.return_value = Mock(id="price_new_monthly")

    sync_plan_to_stripe(plan)

    assert plan.stripe_yearly_price_id is None
    mock_stripe.Price.modify.assert_any_call("price_old_yearly", active=False)
