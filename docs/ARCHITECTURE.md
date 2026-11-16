# Architecture - CloudOps Pulse

## Overview

CloudOps Pulse is a small monitoring API with a production-style delivery
pipeline. The application itself is deliberately simple (one FastAPI service,
in-memory state) so the DevOps story - tests, containers, CI/CD, metrics,
alerts and Infrastructure as Code - stays front and centre.

## Design decisions

| Decision | Why | Trade-off |
|---|---|---|
| FastAPI + Uvicorn only (no extra deps) | Fast startup, small image, easy to audit | Fewer batteries included |
| Prometheus metrics implemented manually | No extra library; shows understanding of the exposition format | Must keep format correct by hand |
| In-memory service registry | Zero setup for demos and tests; state resets are predictable | Data is lost on restart; not multi-instance safe |
| Pure logic in `app/checker.py` | Classification / uptime maths is unit-testable without network | Extra module to maintain |
| Multi-stage Docker build, non-root user | Smaller, safer runtime image | Slightly longer Dockerfile |
| `urllib` for upstream checks (stdlib) | No extra dependency; explicit timeout handling | Less ergonomic than `httpx` / `requests` |
| Terraform: single EC2 + S3 | Free-tier friendly, easy to explain in an interview | Not highly available - no LB / ASG by design |
| Manual-only deploy workflow | Prevents accidental production deploys from every push | Deploys require a deliberate click |

## Request flow

1. A user registers a service with `POST /api/services`.
2. `GET /api/services/{name}/check` performs a real HTTP request (3s timeout),
   measures latency, and classifies the result via `app/checker.py`.
3. History is kept in memory (last 100 checks) and uptime % is derived from it.
4. Every request increments counters exposed at `/metrics` in Prometheus
   text format; Prometheus (docker-compose) scrapes it every 15s.
5. Alert rules in `monitoring/alerts.yml` fire on scrape failure
   (`ServiceDown`) or a high failed-check rate (`HighErrorRate`).

## CI/CD flow

- **CI** (`.github/workflows/ci.yml`): on every push / PR - install dev deps,
  lint, run pytest, then build the Docker image (no push).
- **Deploy** (`.github/workflows/deploy.yml`): manual `workflow_dispatch` only -
  builds and pushes to GHCR, then optionally runs `scripts/deploy.sh` over SSH.
  The SSH job is guarded by a repository variable so it skips cleanly when
  secrets are not configured.

## What I would add next

- Persistent storage (SQLite / Postgres) behind a repository interface
- Background periodic checker (instead of check-on-demand)
- Authentication on write endpoints
- Grafana dashboard JSON and Alertmanager routing
- Terraform remote state (S3 + DynamoDB lock) and an ALB + ASG variant
