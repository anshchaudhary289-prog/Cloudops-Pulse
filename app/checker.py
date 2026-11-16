"""Pure, unit-testable logic for health-check classification.

This module has no network or framework dependencies so it can be
tested in isolation and reused by workers, CLIs or other services.
"""

from __future__ import annotations

from typing import Iterable, Optional


def classify_status(status_code: Optional[int]) -> str:
    """Classify an HTTP status code.

    Returns:
        "up"      for 2xx and 3xx responses
        "down"    for 4xx / 5xx responses
        "unknown" when no response was received (None)
    """
    if status_code is None:
        return "unknown"
    if 200 <= status_code < 400:
        return "up"
    return "down"


def classify_latency(latency_ms: Optional[float]) -> str:
    """Classify a latency measurement in milliseconds."""
    if latency_ms is None:
        return "unknown"
    if latency_ms < 200:
        return "fast"
    if latency_ms < 1000:
        return "slow"
    return "critical"


def calculate_uptime(checks: Iterable[bool]) -> float:
    """Return uptime percentage (0-100) from a sequence of booleans.

    True means the check succeeded. An empty history returns 100.0,
    representing "no failures recorded yet".
    """
    checks = list(checks)
    if not checks:
        return 100.0
    successful = sum(1 for c in checks if c)
    return round((successful / len(checks)) * 100.0, 2)


def is_healthy(status_code: Optional[int], latency_ms: Optional[float] = None,
               latency_threshold_ms: float = 5000.0) -> bool:
    """A check is healthy only if the service is up and not critically slow."""
    if classify_status(status_code) != "up":
        return False
    if latency_ms is not None and latency_ms > latency_threshold_ms:
        return False
    return True


def build_check_result(name: str, url: str, status_code: Optional[int],
                       latency_ms: Optional[float], error: Optional[str] = None) -> dict:
    """Build a normalised check-result dictionary."""
    status = classify_status(status_code)
    if error and status_code is None:
        status = "down"
    return {
        "name": name,
        "url": url,
        "status": status,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2) if latency_ms is not None else None,
        "latency_class": classify_latency(latency_ms),
        "healthy": is_healthy(status_code, latency_ms) and not bool(error and status_code is None),
        "error": error,
    }
