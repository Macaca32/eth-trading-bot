"""
General-purpose utility / helper functions.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def timestamp_ms() -> int:
    """Return current Unix timestamp in milliseconds."""
    return int(time.time() * 1000)


def timestamp_s() -> float:
    """Return current Unix timestamp in seconds."""
    return time.time()


def ms_to_datetime(ms: int) -> datetime:
    """Convert a millisecond Unix timestamp to a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def datetime_to_ms(dt: datetime) -> int:
    """Convert a datetime to a millisecond Unix timestamp."""
    return int(dt.timestamp() * 1000)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide two numbers, returning *default* when denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp *value* between *min_val* and *max_val*."""
    return max(min_val, min(max_val, value))


def round_step(value: float, step: float) -> float:
    """
    Round *value* to the nearest multiple of *step*.

    Useful for respecting exchange tick / lot sizes.
    """
    if step <= 0:
        return value
    return round(value / step) * step


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

from functools import wraps


def retry(max_attempts: int = 3, base_delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator that retries a function on exception with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including the first).
        base_delay: Initial delay in seconds between retries.
        backoff: Multiplier applied to the delay after each retry.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        delay = base_delay * (backoff ** (attempt - 1))
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def chunk_list(lst: list[T], chunk_size: int) -> list[list[T]]:
    """Split *lst* into sub-lists of at most *chunk_size* elements."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    """Flatten a nested dictionary into dot-separated keys."""
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


__all__ = [
    "utc_now", "timestamp_ms", "timestamp_s",
    "ms_to_datetime", "datetime_to_ms",
    "safe_divide", "clamp", "round_step",
    "retry", "chunk_list", "flatten_dict",
]
