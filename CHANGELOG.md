# Changelog

All notable changes to CloudOps Pulse are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 6 new pytest tests (20 total): local-server checks for the up path (HTTP
  200) and the HTTP-error path (HTTP 500), `last_status` / `uptime_percent`
  propagation after a check, `/metrics` reflecting registered services and
  check counters, plus checker boundaries (399/400) and the latency
  threshold.

### Changed

- README project-structure tree and docs links refreshed: `k8s/`,
  `monitoring/grafana-dashboard.json`, `docs/API.md`, `docs/terraform.md`,
  `CHANGELOG.md`, and `.env.example` were missing from the tree even though
  they exist in the repo; the API and Terraform sections now link to their
  full guides.

## [1.0.0] - 2026-11-18

### Added

- Kubernetes manifests under `k8s/` for deploying the app in a cluster:
  `namespace.yaml`, `deployment.yaml` (2 replicas, GHCR image, `/health`
  readiness/liveness probes, non-root user, CPU/memory limits), `service.yaml`
  (ClusterIP on port 8000), and `prometheus-configmap.yaml` (in-cluster scrape
  target plus the alert rules from `monitoring/alerts.yml`).
- `k8s/README.md` with apply, verify, and port-forward instructions.

## [1.0.0] - 2026-11-17

### Added

- Grafana dashboard (`monitoring/grafana-dashboard.json`, 7 panels) for service
  health and checks: scrape-target status, services registered, app uptime,
  up/down check rate, request rate, health-check rate, and total checks.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`): pytest, lint, and a
  Docker image build on every push and pull request.
- Manual deploy workflow (`.github/workflows/deploy.yml`) that builds and
  pushes the image to GHCR.

### Fixed

- Added `pythonpath = ["."]` to the pytest config in `pyproject.toml` so CI
  can import the `app` package.

## [1.0.0] - 2026-11-16

Initial release: a production-style service uptime and health monitoring API
with a complete DevOps pipeline.

### Added

- FastAPI app (`app/main.py`, `app/checker.py`):
  - Service registry — register, list, inspect, and delete services (`name` + `url`).
  - Real health checks — an actual HTTP request per check (3-second timeout),
    with latency measurement and up/down classification; unreachable services
    are handled gracefully instead of crashing the app.
  - Uptime tracking — per-service check history and uptime percentage.
  - Prometheus metrics at `/metrics` in text format, implemented manually
    (no extra library), plus `GET /health` and interactive API docs at `/docs`.
- Tests (`tests/`): 14 pytest tests covering the API and the checker.
- Containerisation: multi-stage `Dockerfile` (non-root user, `HEALTHCHECK`)
  and a `docker-compose.yml` stack (app + Prometheus).
- Monitoring: Prometheus scrape config (`monitoring/prometheus.yml`) and alert
  rules (`monitoring/alerts.yml`).
- Infrastructure as code: Terraform (`terraform/`) provisioning an AWS EC2
  instance, security group, and S3 bucket in `ap-south-1`.
- Helper scripts (`scripts/`): `deploy.sh`, `health-check.sh`, `user_data.sh`.
- Documentation: `README.md` (setup, usage, architecture diagram) and
  `docs/ARCHITECTURE.md`.
