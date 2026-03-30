# EC2 Cloud HTTP Quickstart

This guide applies the repository automation to run the Cloud backend on EC2 and connect local Edge/Frontend.

## 1) Launch EC2 (AWS Console)

1. Region: `ap-northeast-2` (Seoul)
2. AMI: `Ubuntu Server 24.04 LTS`
3. Type: `t3.micro`
4. Create/download key pair (`.pem`)
5. Security Group inbound:
   - `22` from `My IP`
   - `80` from `0.0.0.0/0`
   - `443` optional (future HTTPS)
   - `8000` temporary for bootstrap checks (close after validation)

## 2) Connect to EC2 and deploy backend

From local terminal:

```bash
ssh -i <key>.pem ubuntu@<EC2_PUBLIC_IP>
```

On EC2:

```bash
mkdir -p ~/app
cd ~/app
git clone <YOUR_REPO_URL> stop
cd stop
bash scripts/setup_ec2_cloud.sh
```

If you already know frontend origin, you can set CORS while setup runs:

```bash
FRONTEND_ORIGIN=http://<YOUR_FRONTEND_HOST> bash scripts/setup_ec2_cloud.sh
```

## 3) Fill required Cloud env values

On EC2:

```bash
cd ~/app/stop
nano .env
```

Required keys:

- `AUTH_ADMIN_EMAIL`
- `AUTH_ADMIN_PASSWORD`
- `AUTH_JWT_SECRET`
- `AWS_ACCESS_KEY`
- `AWS_SECRET_KEY`

Recommended DB path on EC2:

- `LOCAL_DB_PATH=/home/ubuntu/app/stop/cloud/data/cloud.db`

Apply:

```bash
sudo systemctl restart conveyor-guard-cloud
sudo systemctl status conveyor-guard-cloud --no-pager
sudo nginx -t
sudo systemctl restart nginx
```

## 4) Verify backend is reachable

On EC2:

```bash
curl http://127.0.0.1:8000/
curl -I http://127.0.0.1/
sudo journalctl -u conveyor-guard-cloud -f
```

From local machine:

```bash
./scripts/verify_ec2_http.sh --ip <EC2_PUBLIC_IP>
```

## 5) Point local Edge/Frontend to EC2

From local repository root:

```bash
./scripts/configure_ec2_targets.sh --ip <EC2_PUBLIC_IP>
```

It updates:

- `.env.edge`: `CLOUD_BASE_URL=http://<EC2_PUBLIC_IP>`
- `frontend/simple-video-viewer/.env`:
  - `REACT_APP_API_BASE_URL=http://<EC2_PUBLIC_IP>`
  - `REACT_APP_WS_BASE_URL=ws://<EC2_PUBLIC_IP>`

Then restart Edge and Frontend.

## 6) Post-check hardening

After checks are done, remove inbound `8000` from security group and keep public traffic only through nginx (`80`/`443`).
