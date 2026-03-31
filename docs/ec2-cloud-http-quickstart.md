# EC2 + Docker + Caddy + Tailscale Quickstart

This guide deploys Cloud + Frontend on one EC2 instance and connects Edge through Tailscale.

## 1) Launch EC2

1. Region: `ap-northeast-2` (Seoul)
2. AMI: `Ubuntu Server 24.04 LTS`
3. Type: `t3.medium`
4. Storage:
   - Root: `30GiB gp3`
   - Data EBS: `100GiB gp3` (encrypted)
5. Security Group inbound:
   - `22` from admin IP (`/32`)
   - `80`, `443` from `0.0.0.0/0`
   - Do not open `8000`

## 2) Connect and prepare host

```bash
ssh -i <key>.pem ubuntu@<EC2_PUBLIC_IP>
```

Install Docker and Compose plugin:

```bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ubuntu
newgrp docker
```

Mount data EBS (example device name):

```bash
sudo mkfs -t ext4 /dev/nvme1n1
sudo mkdir -p /srv/conveyor
sudo mount /dev/nvme1n1 /srv/conveyor
sudo chown -R ubuntu:ubuntu /srv/conveyor
UUID=$(sudo blkid -s UUID -o value /dev/nvme1n1)
echo "UUID=$UUID /srv/conveyor ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
```

## 3) Install and join Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

Use this Tailscale IPv4 for Edge `CLOUD_BASE_URL=http://<TAILSCALE_IP>:8000`.

## 4) Deploy repository

```bash
mkdir -p ~/app
cd ~/app
git clone <YOUR_REPO_URL> stop
cd stop
cp .env.prod.example .env.prod
```

Edit `.env.prod` and set at minimum:

- `CADDY_DOMAIN`
- `ACME_EMAIL`
- `AUTH_ADMIN_EMAIL`
- `AUTH_ADMIN_PASSWORD`
- `AUTH_JWT_SECRET`
- `EDGE_SHARED_SECRET`
- `AWS_S3_BUCKET`
- `AWS_REGION`
- `CONVEYOR_DATA_DIR=/srv/conveyor/data`
- `LOCAL_DB_PATH=/app/cloud/data/cloud.db`

Then run:

```bash
mkdir -p /srv/conveyor/data
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml ps
```

## 5) Verify

```bash
curl -I https://<YOUR_DOMAIN>/
curl -I https://<YOUR_DOMAIN>/docs
docker compose -f docker-compose.prod.yml logs -f cloud
```

## 6) Edge target setup

On Edge machine `.env.edge`:

```env
CLOUD_BASE_URL=http://<TAILSCALE_IP>:8000
EDGE_SHARED_SECRET=<same as cloud>
WEBRTC_ICE_SERVERS_JSON=[{"urls":["stun:stun.l.google.com:19302","turn:<YOUR_DOMAIN>:3478"],"username":"<TURN_USER>","credential":"<TURN_PASSWORD>"}]
```

Restart Edge process after update.

## 7) Host firewall recommendation (UFW)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow in on tailscale0 to any port 8000 proto tcp
sudo ufw allow 3478/tcp
sudo ufw allow 3478/udp
sudo ufw allow 49160:49200/udp
sudo ufw enable
sudo ufw status verbose
```

Do not allow port `8000` on public interfaces.
