# CloudOps Pulse — Terraform Deployment Guide

This guide documents the Terraform configuration in `terraform/` that provisions
CloudOps Pulse on AWS. It is a single-instance, free-tier-friendly deployment
on purpose: one EC2 instance running the Docker image, plus one private S3
bucket for logs and artifacts. There is no load balancer or auto-scaling group
by design — see [Limitations](#limitations).

> Note: this configuration has been reviewed from the code (resources
> cross-checked against `scripts/user_data.sh` and
> `docs/ARCHITECTURE.md`). It has not been applied from this workspace and
> `terraform fmt` / `terraform validate` could not be run here (no Terraform
> binary on this machine) — run `terraform fmt`, `terraform validate` and
> `terraform plan` yourself before applying.

## What gets provisioned

| Resource | File | Details |
| --- | --- | --- |
| EC2 instance | `terraform/main.tf` | `t2.micro`, latest Ubuntu 22.04 LTS AMI from Canonical (`099720109477`), runs the GHCR image via `user_data` |
| Security group | `terraform/main.tf` | Ingress: SSH `22`, HTTP `80`, app port `8000` (default); egress: all. All ingress is `0.0.0.0/0` — see [Security notes](#security-notes) |
| S3 bucket | `terraform/main.tf` | Name prefix `cloudops-pulse-logs-`, versioning enabled, AES-256 encryption at rest, all public access blocked |
| AMI lookup | `terraform/main.tf` | `data "aws_ami" "ubuntu"` — most recent `ubuntu-jammy-22.04-amd64-server-*`, HVM |

The instance boots with `scripts/user_data.sh` (via `templatefile()`): it
installs Docker from Docker's official apt repo, pulls
`ghcr.io/anshchaudhary289-prog/cloudops-pulse:latest`, and runs it as
`cloudops-pulse` with `--restart unless-stopped`, mapping
`$APP_PORT:8000`.

## Files

| File | Purpose |
| --- | --- |
| `terraform/versions.tf` | Terraform `>= 1.5.0`, AWS provider `~> 5.0`, provider region from `var.aws_region` |
| `terraform/variables.tf` | All inputs (see below) |
| `terraform/main.tf` | AMI data source, security group, S3 bucket (+ versioning, encryption, public-access block), EC2 instance |
| `terraform/outputs.tf` | `public_ip`, `app_url`, `health_url`, `s3_bucket` |

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `aws_region` | `ap-south-1` | AWS region to deploy into |
| `instance_type` | `t2.micro` | EC2 instance type (free-tier eligible) |
| `project_name` | `cloudops-pulse` | Used for resource names and tags |
| `docker_image` | `ghcr.io/anshchaudhary289-prog/cloudops-pulse:latest` | Container image run on the instance |
| `app_port` | `8000` | Port the application listens on |

Override on the command line, e.g.
`terraform apply -var="instance_type=t3.micro" -var="app_port=8080"`.

## Deploy

```bash
cd terraform
terraform init
terraform plan        # review what will be created before applying
terraform apply
terraform output app_url      # e.g. http://<public-ip>:8000
terraform output health_url   # e.g. http://<public-ip>:8000/health
```

Prerequisites: Terraform `>= 1.5.0` installed and AWS credentials configured
(for example via `aws configure`). The default region is `ap-south-1`.

Verify the deployment with the health endpoint and the API reference:

```bash
curl "$(terraform output -raw health_url)"
# expected: {"status":"healthy", ...}
```

See [`docs/API.md`](API.md) for the endpoints exposed on the deployed instance.

## Tear down

```bash
cd terraform
terraform destroy
```

Run this when done to avoid charges. The S3 bucket is versioned, so `destroy`
removes the bucket only after its objects/versions are gone; if destroy fails
on a non-empty bucket, empty it first (`aws s3 rm --recursive`).

## Security notes

- The security group opens SSH (`22`), HTTP (`80`) and the app port to
  `0.0.0.0/0`. That is acceptable for a demo, but for anything beyond a demo,
  restrict SSH to your own IP (`cidr_blocks = ["<your-ip>/32"]`).
- The S3 bucket is private by default: versioning on, SSE-S3 (AES-256)
  encryption on, and all four public-access blocks enabled.
- No SSH key pair is attached to the instance (`key_name` is not set), so
  there is no SSH login path into the box as configured — access is via the
  HTTP/app port only. Add a `key_name` if you need shell access.
- State is stored locally (`terraform.tfstate` in this directory) — it is not
  committed to the repo. Do not share the state file; it can contain
  sensitive values.

## Limitations

- **Single instance, no high availability.** No ALB, no Auto Scaling Group.
  If the instance dies, the service is down until Terraform recreates it.
  The app container itself restarts automatically (`--restart
  unless-stopped`).
- **Local state, no locking.** Two people running `apply` at the same time
  can corrupt state. A remote backend (S3 + DynamoDB lock) is the documented
  next step in `docs/ARCHITECTURE.md`.
- **No HTTPS.** The app is served over plain HTTP on the app port.
- **Free-tier scope.** `t2.micro` in `ap-south-1` is free-tier eligible for
  new AWS accounts (750 hrs/month for 12 months); S3 charges are minimal at
  this scale but not zero.

## Related docs

- [`docs/API.md`](API.md) — API reference for the deployed service
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — design notes and trade-offs,
  including the ALB + ASG and remote-state follow-ups
- `README.md` — project overview and the short Terraform quick-start
