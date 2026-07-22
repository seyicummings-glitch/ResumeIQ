# -ResumeIQ
AI Resume Analyzer

## Deployment / HTTPS

The app itself only redirects http→https and adds an HSTS header when the `FORCE_HTTPS` env var is set to `true`. Real TLS certificates are provisioned outside this repo — at a reverse proxy (Nginx/Caddy + Let's Encrypt) or a hosting platform's managed HTTPS. Only set `FORCE_HTTPS=true` once that upstream TLS termination is actually in place; otherwise it just breaks plain-http access with nothing to redirect to.

## Health Check / Uptime Monitoring

`GET /health` returns `{"status": "ok"|"maintenance"|"unhealthy", "database": "connected"|"unreachable", "timestamp": "..."}` and always responds with HTTP 200 (it never raises), so an external uptime monitor (e.g. UptimeRobot, Better Stack, Pingdom) can point at it and alert based on the `status` field or on the request failing/timing out, rather than on HTTP error codes. `status` is `"unhealthy"` if the database is unreachable, and `"maintenance"` while `MAINTENANCE_MODE` is on.

## Maintenance Mode

Set `MAINTENANCE_MODE=true` and restart the app for a planned maintenance window: every route except `/health` returns `503`, while `/health` keeps responding `200` with `status: "maintenance"` so your uptime monitor doesn't false-page during the window. Procedure: set the env var, restart, confirm via `/health`, do the maintenance work, then set it back to `false` and restart.
