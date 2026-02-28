# Mobile Alert System Rollout Guide

## Scope
- Incident ingestion from Edge (`/api/edge/incidents`, `/api/edge/incidents/{id}/snapshot`)
- Incident query APIs for web/mobile (`/api/incidents*`)
- Mobile device token registration (`/api/mobile/devices/*`)
- Evacuation graph CRUD + route API (`/api/evacuation/*`)
- Bearer token support for mobile clients

## Current Runtime Notes
- Cloud remains SQLite-based by default (`LOCAL_DB_PATH`).
- Snapshot files are stored under `INCIDENT_SNAPSHOT_DIR` (default: `cloud/data/incidents`).
- Push delivery service is scaffolded:
  - device token persistence and fan-out bookkeeping are implemented
  - real FCM/APNs sending is intentionally left as next step

## Edge Integration
- New detectors:
  - `edge/detect/fire_detector.py`
  - `edge/detect/entrapment_detector.py`
- New edge env knobs:
  - `EDGE_FIRE_RATIO_THRESHOLD`
  - `EDGE_ENTRAPMENT_FRAME_THRESHOLD`
  - `EDGE_INCIDENT_COOLDOWN_SEC`
- Pipeline now publishes incident metadata + JPEG snapshot to Cloud.

## Mobile App (Flutter) API Contract
1. Login
- `POST /api/auth/login`
- use `access_token` from response body

2. Device registration
- `POST /api/mobile/devices/register`
- header: `Authorization: Bearer <access_token>`

3. Incident feed
- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- `GET /api/incidents/{incident_id}/snapshot`

4. Evacuation route
- `GET /api/evacuation/route?edge_id=...&zone_id=...&incident_type=...`

## Production Upgrade Path (AWS)
1. Replace SQLite with RDS(PostgreSQL) behind repository/service abstraction.
2. Store snapshots in S3 and return signed URL or CloudFront URL.
3. Implement actual push sender in `MobilePushService` using FCM/APNs credentials from Secrets Manager.
4. Run Cloud API on ECS Fargate with ALB + ACM.
