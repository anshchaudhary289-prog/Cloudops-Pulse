#!/bin/bash
# EC2 user_data: install Docker and run CloudOps Pulse.
# Terraform templatefile() substitutes ${docker_image} and ${app_port};
# when run outside Terraform those fall back to defaults below.
set -euxo pipefail

DOCKER_IMAGE="${docker_image}"
APP_PORT="${app_port}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable"   > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

docker pull "$DOCKER_IMAGE" || true
docker rm -f cloudops-pulse || true
docker run -d --name cloudops-pulse --restart unless-stopped \
  -p "$APP_PORT:8000" "$DOCKER_IMAGE"
