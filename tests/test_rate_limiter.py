from app.services.rate_limiter import is_rate_limited, reset_rate_limits


def setup_function():
    reset_rate_limits()


def test_allows_requests_under_the_limit():
    for _ in range(5):
        assert is_rate_limited("client-a", 5) is False


def test_blocks_requests_over_the_limit():
    for _ in range(5):
        is_rate_limited("client-b", 5)
    assert is_rate_limited("client-b", 5) is True


def test_clients_are_tracked_independently():
    for _ in range(5):
        is_rate_limited("client-c", 5)
    assert is_rate_limited("client-c", 5) is True
    assert is_rate_limited("client-d", 5) is False


def test_zero_or_negative_limit_disables_limiting():
    for _ in range(100):
        assert is_rate_limited("client-e", 0) is False
    for _ in range(100):
        assert is_rate_limited("client-f", -1) is False


def test_reset_clears_state():
    for _ in range(5):
        is_rate_limited("client-g", 5)
    assert is_rate_limited("client-g", 5) is True
    reset_rate_limits()
    assert is_rate_limited("client-g", 5) is False
