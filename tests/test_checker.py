from app.checker import (
    build_check_result,
    calculate_uptime,
    classify_latency,
    classify_status,
    is_healthy,
)


def test_classify_status_up():
    assert classify_status(200) == "up"
    assert classify_status(201) == "up"
    assert classify_status(301) == "up"


def test_classify_status_down_and_unknown():
    assert classify_status(404) == "down"
    assert classify_status(500) == "down"
    assert classify_status(None) == "unknown"


def test_calculate_uptime():
    assert calculate_uptime([]) == 100.0
    assert calculate_uptime([True, True, True]) == 100.0
    assert calculate_uptime([True, False]) == 50.0
    assert calculate_uptime([False, False]) == 0.0
    assert calculate_uptime([True, True, False]) == 66.67


def test_classify_latency():
    assert classify_latency(50) == "fast"
    assert classify_latency(500) == "slow"
    assert classify_latency(2500) == "critical"
    assert classify_latency(None) == "unknown"


def test_is_healthy_and_build_result():
    assert is_healthy(200, 100) is True
    assert is_healthy(500, 100) is False
    assert is_healthy(None, None) is False
    result = build_check_result("api", "https://example.com", 200, 42.5)
    assert result["status"] == "up"
    assert result["healthy"] is True
    assert result["latency_ms"] == 42.5
    down = build_check_result("api", "https://example.com", None, 3000.0, error="Timeout")
    assert down["status"] == "down"
    assert down["healthy"] is False
    assert down["error"] == "Timeout"
