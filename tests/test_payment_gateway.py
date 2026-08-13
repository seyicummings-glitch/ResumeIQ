from app.services.payment_gateway import process_payment, SUPPORTED_METHODS


def test_process_payment_succeeds_for_each_supported_method():
    for method in SUPPORTED_METHODS:
        result = process_payment(method, 999, "usd")
        assert result.status == "succeeded"
        assert result.external_reference.startswith("MOCK-TX-")


def test_process_payment_rejects_unsupported_method():
    result = process_payment("check", 999, "usd")
    assert result.status == "failed"
    assert result.external_reference == ""
    assert "Unsupported" in result.message


def test_process_payment_rejects_non_positive_amount():
    result = process_payment("credit_card", 0, "usd")
    assert result.status == "failed"

    result = process_payment("credit_card", -100, "usd")
    assert result.status == "failed"


def test_process_payment_references_are_unique():
    first = process_payment("credit_card", 500, "usd")
    second = process_payment("credit_card", 500, "usd")
    assert first.external_reference != second.external_reference
