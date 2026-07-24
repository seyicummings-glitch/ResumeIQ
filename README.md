# -ResumeIQ
AI Resume Analyzer

## Deployment / HTTPS

The app itself only redirects http→https and adds an HSTS header when the `FORCE_HTTPS` env var is set to `true`. Real TLS certificates are provisioned outside this repo — at a reverse proxy (Nginx/Caddy + Let's Encrypt) or a hosting platform's managed HTTPS. Only set `FORCE_HTTPS=true` once that upstream TLS termination is actually in place; otherwise it just breaks plain-http access with nothing to redirect to.

## Health Check / Uptime Monitoring

`GET /health` returns `{"status": "ok"|"maintenance"|"unhealthy", "database": "connected"|"unreachable", "timestamp": "..."}` and always responds with HTTP 200 (it never raises), so an external uptime monitor (e.g. UptimeRobot, Better Stack, Pingdom) can point at it and alert based on the `status` field or on the request failing/timing out, rather than on HTTP error codes. `status` is `"unhealthy"` if the database is unreachable, and `"maintenance"` while `MAINTENANCE_MODE` is on.

## Maintenance Mode

Set `MAINTENANCE_MODE=true` and restart the app for a planned maintenance window: every route except `/health` returns `503`, while `/health` keeps responding `200` with `status: "maintenance"` so your uptime monitor doesn't false-page during the window. Procedure: set the env var, restart, confirm via `/health`, do the maintenance work, then set it back to `false` and restart.

## AI Resume Suggestions

`POST /resume/ai-suggestions` uses the Claude API (`claude-opus-4-8`) to generate resume improvement suggestions, optionally tailored to a target job description. It's optional infrastructure: set `ANTHROPIC_API_KEY` in `.env` to enable real AI suggestions. Without a key — or if the API call fails (rate limit, connection error, any other API error) — the endpoint doesn't error out; it falls back to suggestions generated from this project's own rule-based analysis (ATS score issues, missing keywords), and the response's `source` field reports which path served the result: `"ai"` or `"fallback"`.

## Backups & Failure Recovery

The primary safety net is Supabase's own backups: enable **Point-in-Time Recovery** (or at minimum daily backups) in the Supabase project dashboard — that's real, automated, and outside this repo's control.

As a supplementary manual/scheduled export, `scripts/backup_db.py` runs `pg_dump` against `DATABASE_URL` and writes a timestamped `.dump` file to `backups/` (gitignored — dumps contain user data, never commit them). Requires a local PostgreSQL client (`pg_dump` on PATH). Run manually with `python scripts/backup_db.py`, or schedule it (cron / Windows Task Scheduler) for regular exports.

**Restore:** `pg_restore --clean --if-exists -d <DATABASE_URL> <dump_file>`

**Failure recovery runbook:** if `/health` reports `"database": "unreachable"`, restore from the most recent Supabase backup (fastest option), or fall back to the latest local `pg_dump` file with the restore command above.

## Load Testing

`scripts/load_test.py` fires concurrent requests at a running instance and reports success rate and latency percentiles, using `concurrent.futures.ThreadPoolExecutor` and the existing `requests` dependency (no extra install needed):

```
python scripts/load_test.py --url http://127.0.0.1:8001/health --requests 200 --concurrency 20
```

This requires a live server to point at — it's a manual diagnostic script, not part of the `pytest` suite. Watch the success rate (should be 100% for `/health` under reasonable load) and p95 latency to gauge how the app holds up under concurrency.
