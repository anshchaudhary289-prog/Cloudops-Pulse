import pytest
from fastapi.testclient import TestClient

from app.main import app, check_history, services

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    services.clear()
    check_history.clear()
    yield
    services.clear()
    check_history.clear()


def test_root_returns_service_info():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "CloudOps Pulse"
    assert "version" in data


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["uptime_seconds"] >= 0
    assert data["version"]


def test_metrics_prometheus_format():
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "cloudops_requests_total" in text
    assert "cloudops_services_registered" in text
    assert "# TYPE" in text


def test_create_and_list_services():
    resp = client.post("/api/services", json={"name": "example", "url": "https://example.com"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "example"

    listing = client.get("/api/services")
    assert listing.status_code == 200
    assert listing.json()["count"] == 1
    assert listing.json()["services"][0]["url"] == "https://example.com"


def test_create_duplicate_service_conflict():
    client.post("/api/services", json={"name": "dup", "url": "https://example.com"})
    resp = client.post("/api/services", json={"name": "dup", "url": "https://example.com"})
    assert resp.status_code == 409


def test_create_service_validation():
    resp = client.post("/api/services", json={"name": "bad"})
    assert resp.status_code == 422
    resp2 = client.post("/api/services", json={"name": "bad2", "url": "ftp://example.com"})
    assert resp2.status_code == 422


def test_get_and_delete_service():
    client.post("/api/services", json={"name": "temp", "url": "https://example.com"})
    got = client.get("/api/services/temp")
    assert got.status_code == 200
    deleted = client.delete("/api/services/temp")
    assert deleted.status_code == 204
    missing = client.get("/api/services/temp")
    assert missing.status_code == 404


def test_get_unknown_service_404():
    assert client.get("/api/services/nope").status_code == 404
    assert client.get("/api/services/nope/check").status_code == 404
    assert client.delete("/api/services/nope").status_code == 404


def test_check_unreachable_service_is_graceful():
    # Port 9 (discard) on localhost is effectively unreachable for HTTP.
    client.post("/api/services", json={"name": "downsvc", "url": "http://127.0.0.1:9"})
    resp = client.get("/api/services/downsvc/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "down"
    assert data["healthy"] is False
    assert data["latency_ms"] is not None
