#!/usr/bin/env bash
set -euo pipefail

# Run this script on Ubuntu 24.04 EC2.

APP_DIR="${APP_DIR:-$HOME/app/stop}"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
CONVEYOR_DATA_DIR="${CONVEYOR_DATA_DIR:-/srv/conveyor/data}"

echo "[1/6] Install Docker + Compose"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git gnupg
sudo install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
fi
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"

echo "[2/6] Validate app dir: $APP_DIR"
if [[ ! -d "$APP_DIR" ]]; then
  echo "[ERROR] APP_DIR not found: $APP_DIR" >&2
  echo "Clone repo first. Example:"
  echo "  mkdir -p \$HOME/app && cd \$HOME/app && git clone <repo-url> stop"
  exit 1
fi

cd "$APP_DIR"

echo "[3/6] Prepare env file"
if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f ".env.prod.example" ]]; then
    cp .env.prod.example "$ENV_FILE"
    echo "[INFO] Created $ENV_FILE from .env.prod.example"
  else
    echo "[ERROR] Missing .env.prod.example and $ENV_FILE" >&2
    exit 1
  fi
fi

for required_key in CADDY_DOMAIN ACME_EMAIL AUTH_ADMIN_EMAIL AUTH_ADMIN_PASSWORD AUTH_JWT_SECRET EDGE_SHARED_SECRET AWS_S3_BUCKET; do
  if ! grep -q "^${required_key}=" "$ENV_FILE"; then
    echo "[WARN] Missing $required_key in $ENV_FILE"
  fi
done

echo "[4/6] Prepare persistent data directory"
sudo mkdir -p "$CONVEYOR_DATA_DIR"
sudo chown -R "$USER":"$USER" "$CONVEYOR_DATA_DIR"

if ! grep -q "^CONVEYOR_DATA_DIR=" "$ENV_FILE"; then
  echo "CONVEYOR_DATA_DIR=$CONVEYOR_DATA_DIR" >>"$ENV_FILE"
  echo "[INFO] Added CONVEYOR_DATA_DIR=$CONVEYOR_DATA_DIR to $ENV_FILE"
fi

echo "[5/6] Build and start compose stack"
sudo docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

echo "[6/6] Show status"
sudo docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

cat <<EOF

[DONE] EC2 production stack started.

Next:
  1) Configure UFW to allow 80/443 and tailscale0:8000 only.
  2) Join Tailscale and point Edge CLOUD_BASE_URL to tailscale IP.
  3) Verify:
     curl -I https://<YOUR_DOMAIN>/
     curl -I https://<YOUR_DOMAIN>/docs
EOF
