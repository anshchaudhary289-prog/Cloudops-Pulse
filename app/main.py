"""CloudOps Pulse - service uptime / health monitoring API.

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.checker import build_check_result, calculate_uptime

VERSION = "1.0.0"
START_TIME = time.time()

app = FastAPI(
    title="CloudOps Pulse",
    description="Production-style service uptime and health monitoring API with Prometheus metrics.",
    version=VERSION,
)

# ---------------------------------------------------------------------------
# In-memory state (intentionally simple; see docs/ARCHITECTURE.md trade-offs)
# ---------------------------------------------------------------------------
services: dict[str, dict] = {}
check_history: dict[str, list[bool]] = {}

counters = {
    "requests_total": 0,
    "health_checks_total": 0,
    "service_checks_total": 0,
    "service_checks_up": 0,
    "service_checks_down": 0,
}


@app.middleware("http")
async def count_requests(request: Request, call_next):
    counters["requests_total"] += 1
    response = await call_next(request)
    return response


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, examples=["my-api"])
    url: str = Field(..., min_length=7, examples=["https://example.com"])


class ServiceOut(BaseModel):
    name: str
    url: str
    created_at: str
    last_status: Optional[str] = None
    uptime_percent: float = 100.0


def _service_out(record: dict) -> dict:
    history = check_history.get(record["name"], [])
    return {
        "name": record["name"],
        "url": record["url"],
        "created_at": record["created_at"],
        "last_status": record.get("last_status"),
        "uptime_percent": calculate_uptime(history),
    }


@app.get("/")
def root():
    """Service information."""
    return {
        "service": "CloudOps Pulse",
        "version": VERSION,
        "description": "Service uptime and health monitoring API",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "services_endpoint": "/api/services",
    }


@app.get("/health")
def health():
    """Liveness / readiness probe used by Docker HEALTHCHECK and scripts."""
    counters["health_checks_total"] += 1
    return {
        "status": "healthy",
        "version": VERSION,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services_registered": len(services),
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus text exposition format (implemented manually, no extra lib)."""
    uptime = round(time.time() - START_TIME, 2)
    lines = [
        "# HELP cloudops_requests_total Total HTTP requests received",
        "# TYPE cloudops_requests_total counter",
        f"cloudops_requests_total {counters['requests_total']}",
        "# HELP cloudops_health_checks_total Total /health calls",
        "# TYPE cloudops_health_checks_total counter",
        f"cloudops_health_checks_total {counters['health_checks_total']}",
        "# HELP cloudops_service_checks_total Total upstream service checks performed",
        "# TYPE cloudops_service_checks_total counter",
        f"cloudops_service_checks_total {counters['service_checks_total']}",
        "# HELP cloudops_service_checks_up Upstream checks classified up",
        "# TYPE cloudops_service_checks_up counter",
        f"cloudops_service_checks_up {counters['service_checks_up']}",
        "# HELP cloudops_service_checks_down Upstream checks classified down",
        "# TYPE cloudops_service_checks_down counter",
        f"cloudops_service_checks_down {counters['service_checks_down']}",
        "# HELP cloudops_services_registered Currently registered services",
        "# TYPE cloudops_services_registered gauge",
        f"cloudops_services_registered {len(services)}",
        "# HELP cloudops_uptime_seconds Seconds since process start",
        "# TYPE cloudops_uptime_seconds gauge",
        f"cloudops_uptime_seconds {uptime}",
        "# HELP cloudops_app_info Application info",
        "# TYPE cloudops_app_info gauge",
        f'cloudops_app_info{{version="{VERSION}"}} 1',
        "",
    ]
    return PlainTextResponse(content="\n".join(lines), media_type="text/plain; version=0.0.4")


@app.get("/api/services")
def list_services():
    return {"count": len(services), "services": [_service_out(s) for s in services.values()]}


@app.post("/api/services", status_code=201)
def create_service(payload: ServiceCreate):
    if not (payload.url.startswith("http://") or payload.url.startswith("https://")):
        raise HTTPException(status_code=422, detail="url must start with http:// or https://")
    if payload.name in services:
        raise HTTPException(status_code=409, detail=f"Service '{payload.name}' already exists")
    record = {
        "name": payload.name,
        "url": payload.url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_status": None,
    }
    services[payload.name] = record
    check_history[payload.name] = []
    return _service_out(record)


@app.get("/api/services/{name}")
def get_service(name: str):
    record = services.get(name)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return _service_out(record)


@app.delete("/api/services/{name}", status_code=204)
def delete_service(name: str):
    if name not in services:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    del services[name]
    check_history.pop(name, None)
    return None


@app.get("/api/services/{name}/check")
def check_service(name: str):
    """Perform a real HTTP check against the registered service URL."""
    record = services.get(name)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")

    url = record["url"]
    counters["service_checks_total"] += 1
    started = time.perf_counter()
    status_code: Optional[int] = None
    error: Optional[str] = None

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CloudOpsPulse/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310 - user-registered URL is the product feature
            status_code = resp.getcode()
            resp.read(512)
    except urllib.error.HTTPError as exc:
        # An HTTP error response is still a response from the service.
        status_code = exc.code
    except Exception as exc:  # unreachable, DNS, timeout, TLS, etc. - handle gracefully
        error = f"{type(exc).__name__}: {exc}"

    latency_ms = (time.perf_counter() - started) * 1000.0
    result = build_check_result(name, url, status_code, latency_ms, error=error)
    result["checked_at"] = datetime.now(timezone.utc).isoformat()

    record["last_status"] = result["status"]
    check_history.setdefault(name, []).append(result["status"] == "up")
    # Keep history bounded
    if len(check_history[name]) > 100:
        check_history[name] = check_history[name][-100:]

    if result["status"] == "up":
        counters["service_checks_up"] += 1
    else:
        counters["service_checks_down"] += 1

    result["uptime_percent"] = calculate_uptime(check_history[name])
    return result
