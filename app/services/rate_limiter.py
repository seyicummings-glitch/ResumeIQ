"""
In-memory fixed-window rate limiter, keyed by client identifier (IP).

Single-process only: if the app runs multiple worker processes, each one
enforces its own independent limit rather than a shared global count. That's
a real, documented constraint of the in-memory approach — a distributed
store (Redis) would be needed to enforce one true limit across processes.
"""
import time

_WINDOW_SECONDS = 60
_hits: dict[str, list[float]] = {}


def is_rate_limited(client_id: str, limit_per_minute: int) -> bool:
    """Records a hit for client_id and returns whether it exceeds limit_per_minute
    within the trailing 60-second window. A limit <= 0 disables limiting."""
    if limit_per_minute <= 0:
        return False

    now = time.monotonic()
    window_start = now - _WINDOW_SECONDS
    timestamps = _hits.setdefault(client_id, [])

    while timestamps and timestamps[0] < window_start:
        timestamps.pop(0)

    if len(timestamps) >= limit_per_minute:
        return True

    timestamps.append(now)
    return False


def reset_rate_limits() -> None:
    """Test-only helper to clear all recorded state between test runs."""
    _hits.clear()
