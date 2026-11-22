import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from app.main import app, check_history, services

client = TestClient(app)


class _StatusHandler(BaseHTTPRequestHandler):
    """Serves a fixed status code; the code is set per test via the class attr."""

    status_code = 200

    def do_GET(self):
        self.send_response(self.status_code)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@contextmanager
def local_server(status_code: int):
    """Run a tiny HTTP server on an ephemeral localhost port."""
    _StatusHandler.status_code = status_code
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StatusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _metric_value(text: str, name: str) -> float:
    for line in text.splitlines():
        if line.startswith(name + " ") or line.startswith(name + "{"):
            return float(line.rsplit(" ", 1)[1])
    raise AssertionError(f"metric {name} not found in /metrics output")


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


def test_check_up_service_updates_last_status_and_uptime():
    with local_server(200) as url:
        client.post("/api/services", json={"name": "upsvc", "url": url})
        resp = client.get("/api/services/upsvc/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "up"
    assert data["status_code"] == 200
    assert data["healthy"] is True
    assert data["latency_class"] in ("fast", "slow", "critical")
    assert data["uptime_percent"] == 100.0

    got = client.get("/api/services/upsvc")
    assert got.json()["last_status"] == "up"
    assert got.json()["uptime_percent"] == 100.0


def test_check_http_error_response_is_down():
    # An HTTP 500 is still a response (urllib HTTPError branch), not a crash.
    with local_server(500) as url:
        client.post("/api/services", json={"name": "errsvc", "url": url})
        resp = client.get("/api/services/errsvc/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "down"
    assert data["status_code"] == 500
    assert data["healthy"] is False
    assert data["error"] is None

    got = client.get("/api/services/errsvc")
    assert got.json()["last_status"] == "down"
    assert got.json()["uptime_percent"] == 0.0


def test_metrics_reflect_registered_services_and_checks():
    with local_server(200) as url:
        client.post("/api/services", json={"name": "metricsvc", "url": url})
        text = client.get("/metrics").text
        assert _metric_value(text, "cloudops_services_registered") == 1
        assert 'cloudops_app_info{version="1.0.0"} 1' in text

        before = _metric_value(text, "cloudops_service_checks_total")
        client.get("/api/services/metricsvc/check")
        after = _metric_value(client.get("/metrics").text, "cloudops_service_checks_total")
    assert after == before + 1
