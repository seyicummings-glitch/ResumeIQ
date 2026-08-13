# ResumeIQ

AI-assisted resume analysis and career toolkit for job seekers — upload a resume, match it against
job descriptions, and get a scored breakdown of skills, experience, and qualifications. Also
includes an AI resume builder, skill assessment, interview practice, a learning roadmap, a career
coach, GitHub profile analysis, and a full admin panel with a token-based subscription/billing
system.

This repository is a monorepo: the FastAPI backend lives at the root (`app/`, `tests/`,
`scripts/`), and the React frontend lives alongside it (`src/`, `public/`).

## Features

- **Dashboard** — resume-to-job match scores and saved job recommendations
- **Resume upload & analysis** — ATS compatibility score, keyword matching, AI-powered suggestions
- **Job descriptions** — parse from pasted text, an uploaded file, or a URL
- **AI Resume Builder** — a ChatGPT-style conversational builder with per-conversation history
  (new chat / switch / delete), saved as a new resume version, with selectable templates
- **Resume Version History** — every saved version, with side-by-side score comparison
- **Skill Assessment** — a quiz personalized to your resume's skills and gaps
- **Interview Practice** — voice or text mock interviews with AI feedback, generated from your
  skill gaps
- **Learning Roadmap** — a phased plan with resources to close your skill gaps, with progress
  tracking
- **Career Coach** — an always-available AI chat for career advice
- **GitHub Profile Analysis** — anonymous, no login required
- **Documents** — generated PDF analysis reports, downloadable anytime
- **Subscription & billing** — a shared AI token balance, a free signup grant, a periodic free
  refresh, paid plans, and one-time token packages, all admin-configurable — never stores card
  details
- **Admin panel** — user management, reports, platform settings, AI feature/token configuration,
  plans & billing, analytics/revenue, and skill resources (admin role only)
- **Light/dark theme** with a persisted preference

## Tech stack

**Backend:** FastAPI, SQLAlchemy, PostgreSQL (Supabase-hosted), Google Gemini (with Groq as an
automatic fallback) for AI features.

**Frontend:** [React 19](https://react.dev/) + [Vite](https://vite.dev/),
[React Router v7](https://reactrouter.com/), [TanStack Query](https://tanstack.com/query),
[Tailwind CSS v4](https://tailwindcss.com/) (CSS custom-property design tokens, see
`src/index.css`), [React Hook Form](https://react-hook-form.com/) + [Zod](https://zod.dev/),
[Recharts](https://recharts.org/), [lucide-react](https://lucide.dev/).

## Getting started

### Backend

```bash
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env        # fill in DATABASE_URL, GEMINI_API_KEY, etc.
uvicorn app.main:app --reload --port 8001
```

Run the test suite with `pytest`.

### Frontend

```bash
npm install
cp .env.example .env
npm run dev
```

Opens at `http://localhost:5173` (or the next free port). The backend has no CORS middleware
configured, so in development the frontend never calls it directly — Vite's dev server proxies
`/api/*` requests to it instead. Make sure `VITE_API_PROXY_TARGET` in `.env` matches whatever port
your backend is actually running on.

```bash
npm run build    # production build
npm run preview  # preview a production build locally
npm run lint      # oxlint
```

## Project structure

```
app/              # FastAPI backend
  models/         # SQLAlchemy models
  routes/         # API route handlers
  services/       # business logic, AI integrations
scripts/          # one-off/maintenance scripts (migrations, seeding, backups, load testing)
tests/            # pytest suite

src/              # React frontend
  api/            # one module per backend resource, all built on api/client.js's apiRequest()
  auth/           # auth context, protected/admin route guards, token storage
  components/
    charts/       # recharts wrappers (score gauge, breakdown bars, trend line)
    layout/       # app shell, sidebar nav, header
    subscription/ # token balance badge, upgrade modal
    ui/           # shared primitives (Button, Card, Input, Modal, Table, Toast, ...)
  hooks/          # TanStack Query hooks, one per resource
  pages/          # route-level components
  theme/          # light/dark theme context
```

Design tokens (colors, fonts) live as CSS custom properties in `src/index.css` and are mapped into
Tailwind via `@theme`, with a `.light` class override for light mode.

---

## Backend reference

### Deployment / HTTPS

The app itself only redirects http→https and adds an HSTS header when the `FORCE_HTTPS` env var is
set to `true`. Real TLS certificates are provisioned outside this repo — at a reverse proxy
(Nginx/Caddy + Let's Encrypt) or a hosting platform's managed HTTPS. Only set `FORCE_HTTPS=true`
once that upstream TLS termination is actually in place; otherwise it just breaks plain-http access
with nothing to redirect to.

### Health Check / Uptime Monitoring

`GET /health` returns `{"status": "ok"|"maintenance"|"unhealthy", "database":
"connected"|"unreachable", "timestamp": "..."}` and always responds with HTTP 200 (it never
raises), so an external uptime monitor (e.g. UptimeRobot, Better Stack, Pingdom) can point at it
and alert based on the `status` field or on the request failing/timing out, rather than on HTTP
error codes. `status` is `"unhealthy"` if the database is unreachable, and `"maintenance"` while
`MAINTENANCE_MODE` is on.

### Maintenance Mode

Two ways to trigger it: set `MAINTENANCE_MODE=true` and restart (a hard override that works even
if the database is unreachable), or toggle "Maintenance mode" on the Admin Settings page (`PUT
/admin/settings`) — that one takes effect immediately, no restart needed, since the request
middleware reads it live from the database on every request. Either way: every route except
`/health`, `/auth`, and `/admin` returns `503` (the last two stay reachable so an admin can log in
and turn it back off), while `/health` keeps responding `200` with `status: "maintenance"` so your
uptime monitor doesn't false-page during the window.

### Admin Settings enforcement

The rest of the Admin Settings page is fully wired to real enforcement, not just stored values:

- **AI suggestions enabled** — when off, `/resume/ai-suggestions`, `/matching/{id}/suggestions`,
  `/resume-builder/generate`, and `/interview/chat` (all Gemini-backed) skip the AI API call and go
  straight to their rule-based fallback, regardless of whether an API key is configured.
- **Max upload size / allowed file types** — enforced on every resume upload route
  (`/resume/upload`, `/structure`, `/ats-score`, `/ai-suggestions`, `/save`), read live from the
  database instead of a fixed constant.
- **Rate limit (requests/minute)** — enforced by an in-memory, per-client-IP fixed-window limiter
  (`app/services/rate_limiter.py`) on every route except `/health`. Single-process only: if you run
  multiple worker processes, each enforces its own independent limit rather than one shared count —
  a distributed store (Redis) would be needed for that.
- **Support email** — surfaced in the `503` maintenance response and `429` rate-limit response
  bodies.
- **Free signup tokens / free token refresh interval** — how many AI tokens a brand-new account
  starts with, and how often a Free-plan account's balance is topped back up once it runs out. See
  `app/services/feature_gate.py`.

### AI-powered features

All AI features are backed by the Gemini API (with Groq as an automatic secondary fallback on
rate-limit); set `GEMINI_API_KEY` (and optionally `GEMINI_API_KEY_2`, `GROQ_API_KEY`) in `.env` to
enable them. Every one of them degrades gracefully without a key, or if a call fails — never a raw
error, always a rule-based/deterministic fallback (never fabricating what it can't infer), and the
response's `source` field reports which path served the result: `"ai"` or `"fallback"`.

- **Resume Suggestions** (`POST /resume/ai-suggestions`) — resume improvement suggestions,
  optionally tailored to a target job description.
- **Mock Interview** (`POST /interview/chat`, `POST /interview/sessions`) — turn-by-turn questions
  and feedback, plus a post-session report, grounded in the candidate's saved resume and target job
  description.
- **AI Resume Builder** (`POST /resume-builder/chat`, `/resume-builder/save`,
  `/resume-builder/generate`) — a ChatGPT-style conversational builder. The frontend sends the
  running transcript plus the current structured draft and gets back a reply and the updated draft;
  it's stateless server-side and always grounds on whatever resume is currently active on the
  user's account, if any.
- **Learning Roadmap, Skill Assessment, Career Coach, Documents** — see the corresponding route
  modules in `app/routes/` for details.

### AI Token Economy

Every AI feature has an admin-configurable token cost (`app/models/subscription_models.py`'s
`AiFeatureSetting`); a new account gets a free signup grant, a Free-plan account's balance
periodically refreshes, and paid plans grant tokens per billing period. See
`app/services/feature_gate.py` for the full model and `app/routes/admin_subscriptions.py` /
`app/routes/subscriptions.py` for the admin and user-facing endpoints. Payments are processed by a
test-mode-only mock gateway (`app/services/payment_gateway.py`) — no card numbers, CVV, or expiry
dates are ever accepted or stored, only transaction id/status/amount/currency/method.

### Password Reset Emails

`POST /auth/password-reset/request` sends a real reset-link email via SMTP when configured. Set all
of `SMTP_HOST`, `SMTP_USERNAME`, and `SMTP_PASSWORD` in `.env` to enable it (`SMTP_PORT` defaults
to `587`, `SMTP_FROM_EMAIL` defaults to `SMTP_USERNAME`, `FRONTEND_URL` defaults to
`http://localhost:5173` and is used to build the link the user clicks). For Gmail, use an [app
password](https://myaccount.google.com/apppasswords) as `SMTP_PASSWORD`, not your regular password.
Without SMTP configured, the endpoint falls back to dev mode: it returns the reset token directly
in the response instead of emailing it, so local development still works without real SMTP
credentials.

### Backups & Failure Recovery

The primary safety net is Supabase's own backups: enable **Point-in-Time Recovery** (or at minimum
daily backups) in the Supabase project dashboard — that's real, automated, and outside this repo's
control.

As a supplementary manual/scheduled export, `scripts/backup_db.py` runs `pg_dump` against
`DATABASE_URL` and writes a timestamped `.dump` file to `backups/` (gitignored — dumps contain user
data, never commit them). Requires a local PostgreSQL client (`pg_dump` on PATH). Run manually with
`python scripts/backup_db.py`, or schedule it (cron / Windows Task Scheduler) for regular exports.

**Restore:** `pg_restore --clean --if-exists -d <DATABASE_URL> <dump_file>`

**Failure recovery runbook:** if `/health` reports `"database": "unreachable"`, restore from the
most recent Supabase backup (fastest option), or fall back to the latest local `pg_dump` file with
the restore command above.

### Load Testing

`scripts/load_test.py` fires concurrent requests at a running instance and reports success rate and
latency percentiles, using `concurrent.futures.ThreadPoolExecutor` and the existing `requests`
dependency (no extra install needed):

```bash
python scripts/load_test.py --url http://127.0.0.1:8001/health --requests 200 --concurrency 20
```

This requires a live server to point at — it's a manual diagnostic script, not part of the `pytest`
suite. Watch the success rate (should be 100% for `/health` under reasonable load) and p95 latency
to gauge how the app holds up under concurrency.
