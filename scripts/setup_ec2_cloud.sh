#!/usr/bin/env bash
set -euo pipefail

# Run this on Ubuntu 24.04 EC2.

APP_DIR="${APP_DIR:-$HOME/app/stop}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-}"

upsert_env_var() {
  local key="$1"
  local value="$2"
  local file="$3"
  local escaped
  escaped=$(printf '%s\n' "$value" | sed 's/[\/&]/\\&/g')

  if grep -q "^${key}=" "$file"; then
    sed -i "s/^${key}=.*/${key}=${escaped}/" "$file"
  else
    printf "%s=%s\n" "$key" "$value" >>"$file"
  fi
}

echo "[1/6] apt update and base packages"
sudo apt-get update -y
sudo apt-get install -y git nginx python3-venv python3-pip

echo "[2/6] check app directory: $APP_DIR"
if [[ ! -d "$APP_DIR" ]]; then
  echo "[ERROR] APP_DIR not found: $APP_DIR" >&2
  echo "Clone repo first. Example:"
  echo "  mkdir -p \$HOME/app && cd \$HOME/app && git clone <repo-url> stop"
  exit 1
fi

cd "$APP_DIR"

echo "[3/6] python virtualenv"
if [[ ! -d ".venv-cloud" ]]; then
  "$PYTHON_BIN" -m venv .venv-cloud
fi
. .venv-cloud/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-cloud.txt

echo "[4/6] env file"
if [[ ! -f ".env" ]]; then
  if [[ -f ".env.cloud.example" ]]; then
    cp .env.cloud.example .env
    echo "[INFO] Created .env from .env.cloud.example"
  else
    echo "[WARN] .env.cloud.example not found. Create .env manually."
  fi
fi
echo "[INFO] Edit .env and fill AWS/AUTH values before production run."

# Force EC2-friendly DB path unless user already customized.
if grep -q "^LOCAL_DB_PATH=cloud/data/cloud.db$" .env || ! grep -q "^LOCAL_DB_PATH=" .env; then
  upsert_env_var "LOCAL_DB_PATH" "$APP_DIR/cloud/data/cloud.db" ".env"
  echo "[INFO] Set LOCAL_DB_PATH=$APP_DIR/cloud/data/cloud.db"
fi

if [[ -n "$FRONTEND_ORIGIN" ]]; then
  upsert_env_var "CLOUD_CORS_ALLOW_ORIGINS" "$FRONTEND_ORIGIN" ".env"
  echo "[INFO] Set CLOUD_CORS_ALLOW_ORIGINS=$FRONTEND_ORIGIN"
fi

for required_key in AUTH_ADMIN_EMAIL AUTH_ADMIN_PASSWORD AUTH_JWT_SECRET AWS_ACCESS_KEY AWS_SECRET_KEY; do
  if ! grep -q "^${required_key}=" .env; then
    echo "[WARN] Missing .env key: ${required_key}"
    continue
  fi
  current_value="$(grep "^${required_key}=" .env | head -n 1 | cut -d= -f2-)"
  if [[ -z "$current_value" ]]; then
    echo "[WARN] Empty .env value: ${required_key}"
  fi
done

echo "[5/6] systemd service install"
sudo cp deploy/ec2/cloud.service /etc/systemd/system/conveyor-guard-cloud.service
sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$APP_DIR|g" /etc/systemd/system/conveyor-guard-cloud.service
sudo sed -i "s|EnvironmentFile=.*|EnvironmentFile=$APP_DIR/.env|g" /etc/systemd/system/conveyor-guard-cloud.service
sudo sed -i "s|ExecStart=.*|ExecStart=$APP_DIR/.venv-cloud/bin/uvicorn cloud.main:app --host 127.0.0.1 --port 8000|g" /etc/systemd/system/conveyor-guard-cloud.service
sudo sed -i "s|User=.*|User=$USER|g" /etc/systemd/system/conveyor-guard-cloud.service
sudo systemctl daemon-reload
sudo systemctl enable conveyor-guard-cloud.service
sudo systemctl restart conveyor-guard-cloud.service

echo "[6/6] nginx config"
sudo cp deploy/ec2/nginx-cloud.conf /etc/nginx/sites-available/conveyor-guard-cloud
sudo ln -sf /etc/nginx/sites-available/conveyor-guard-cloud /etc/nginx/sites-enabled/conveyor-guard-cloud
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

echo ""
echo "[DONE] EC2 cloud setup completed."
echo "Check service:"
echo "  sudo systemctl status conveyor-guard-cloud --no-pager"
echo "  sudo journalctl -u conveyor-guard-cloud -f"
echo "Health check:"
echo "  curl http://127.0.0.1:8000/"
