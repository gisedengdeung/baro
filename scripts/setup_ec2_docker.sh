#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.prod"

echo "[1/4] Install Docker engine and Compose plugin"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg

if ! command -v docker >/dev/null 2>&1; then
  sudo install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc >/dev/null
    sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

sudo systemctl enable docker
sudo systemctl restart docker
sudo usermod -aG docker "$USER" || true

echo "[2/4] Prepare deploy directories"
mkdir -p "${ROOT_DIR}/.deploy/cloud-data"

echo "[3/4] Prepare .env.prod"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "${ROOT_DIR}/.env.prod.example" "$ENV_FILE"
  echo "[INFO] Created $ENV_FILE from .env.prod.example"
else
  echo "[INFO] Keeping existing $ENV_FILE"
fi

echo "[4/4] Next commands"
cat <<EOF
Edit the production env file:
  nano ${ENV_FILE}

After filling the values:
  docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build

Useful checks:
  docker compose --env-file .env.prod -f docker-compose.prod.yml ps
  docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f cloud caddy coturn

If docker commands fail with a permission error, reconnect the SSH session once so the docker group is applied.
EOF
