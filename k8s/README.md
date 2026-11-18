# Kubernetes manifests

Run CloudOps Pulse on any Kubernetes cluster. The manifests deploy the API
only — Prometheus itself is intentionally not included (bring your own
Prometheus, or keep using `docker-compose` for the local stack). The
`prometheus-configmap.yaml` gives you the in-cluster scrape config and alert
rules to mount into your Prometheus.

## Prerequisites

- `kubectl` configured against a cluster (local kind/minikube is fine).
- The image `ghcr.io/anshchaudhary289-prog/cloudops-pulse:latest` — published
  by the manual deploy workflow (`.github/workflows/deploy.yml`). If the
  package is private, create an `imagePullSecret` and add it to
  `deployment.yaml` first.

## Deploy

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/prometheus-configmap.yaml   # optional, for Prometheus
```

## Verify

```bash
kubectl -n cloudops-pulse rollout status deployment/cloudops-pulse
kubectl -n cloudops-pulse port-forward svc/cloudops-pulse 8000:8000
curl localhost:8000/health    # {"status": "healthy", ...}
curl localhost:8000/metrics   # Prometheus metrics
```

## Notes

- 2 replicas, with liveness/readiness probes on `/health` — same endpoint
  the Docker healthcheck uses.
- Runs as non-root (the image already ships a non-root `appuser`), with
  `allowPrivilegeEscalation: false` and all Linux capabilities dropped.
- Resource requests/limits: 100m/128Mi requested, 500m/256Mi max.
- The Service is `ClusterIP` on port 8000. Expose it with an Ingress or
  `kubectl port-forward` — no LoadBalancer/NodePort is created by default.
- Prometheus scrape target in-cluster is `cloudops-pulse:8000` (the Service
  DNS name). The compose stack still scrapes `app:8000`; see
  `monitoring/prometheus.yml`.
