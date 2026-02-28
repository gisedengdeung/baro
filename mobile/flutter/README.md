# Flutter App Bootstrap Notes

## Minimum screens
- Login
- Incident list
- Incident detail (snapshot + severity + detected time)
- Evacuation route map/steps

## API usage
- Login: `POST /api/auth/login`
- Register device token: `POST /api/mobile/devices/register`
- Incident list/detail:
  - `GET /api/incidents`
  - `GET /api/incidents/{incident_id}`
  - `GET /api/incidents/{incident_id}/snapshot`
- Evacuation route:
  - `GET /api/evacuation/route?edge_id=&zone_id=&incident_type=`

Use `Authorization: Bearer <access_token>` for authenticated mobile requests.

## Next integration
- Firebase Messaging plugin setup (Android/iOS)
- Deep-link to Incident detail on push payload
- Map rendering for route polyline (CustomPainter / map package)
