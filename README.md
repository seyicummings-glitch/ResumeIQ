# ResumeIQ — Frontend

AI-assisted resume analysis, built for job seekers. Upload a resume, match it against job descriptions, and get a scored breakdown of skills, experience, and qualifications — plus AI-powered suggestions, a skill assessment, interview practice questions, a learning roadmap, resume version history, and generated PDF reports.

This is the React frontend. It talks to a separate FastAPI backend (see [Backend](#backend)).

## Features

- **Dashboard** — resume-to-job match scores and saved job recommendations
- **Resume upload & analysis** — ATS compatibility score, keyword matching, AI-powered suggestions
- **Job descriptions** — parse from pasted text, an uploaded file, or a URL
- **AI Resume Builder** — AI-rewritten summary/experience/skills, saved as a new resume version
- **Resume Version History** — every saved version, with side-by-side score comparison
- **Skill Assessment** — a quiz personalized to your resume's skills and gaps
- **Interview Practice** — behavioral, technical, system design, and role-specific questions generated from your skill gaps
- **Learning Roadmap** — a phased plan with resources to close your skill gaps, with progress tracking
- **Documents** — generated PDF analysis reports, downloadable anytime
- **Analysis history** — every past match, most recent first
- **Admin panel** — user management, reports, analytics, and settings (admin role only)
- **Light/dark theme** with a persisted preference

## Tech stack

- [React 19](https://react.dev/) + [Vite](https://vite.dev/)
- [React Router v7](https://reactrouter.com/) for routing
- [TanStack Query](https://tanstack.com/query) for server state (data fetching, caching, mutations)
- [Tailwind CSS v4](https://tailwindcss.com/) for styling, driven by CSS custom-property design tokens (see `src/index.css`)
- [React Hook Form](https://react-hook-form.com/) + [Zod](https://zod.dev/) for form validation
- [Recharts](https://recharts.org/) for charts
- [lucide-react](https://lucide.dev/) for icons

## Getting started

### Prerequisites

- Node.js 18+
- The [backend](#backend) running locally (see that repo's README)

### Setup

```bash
npm install
cp .env.example .env
```

Edit `.env` if your backend runs somewhere other than the default:

```env
# Base path the frontend uses for API calls. In dev this is proxied by Vite
# straight through to the backend, so leave it as /api.
VITE_API_BASE_URL=/api

# Where the Vite dev proxy forwards /api/* requests to — point this at your
# locally running backend.
VITE_API_PROXY_TARGET=http://127.0.0.1:8001
```

> The backend has no CORS middleware configured, so in development the frontend never calls it directly — Vite's dev server proxies `/api/*` requests to it instead. Make sure `VITE_API_PROXY_TARGET` matches whatever port your backend is actually running on.

### Run

```bash
npm run dev
```

Opens at `http://localhost:5173` (or the next free port).

### Other scripts

```bash
npm run build    # production build
npm run preview  # preview a production build locally
npm run lint      # oxlint
```

## Project structure

```
src/
  api/          # one module per backend resource, all built on api/client.js's apiRequest()
  auth/         # auth context, protected/admin route guards, token storage
  components/
    charts/     # recharts wrappers (score gauge, breakdown bars, trend line)
    layout/     # app shell, sidebar nav, header, footer
    ui/         # shared primitives (Button, Card, Input, Modal, Table, Toast, ...)
  hooks/        # TanStack Query hooks, one per resource
  lib/          # small shared utilities (score bands, file validation)
  pages/        # route-level components
  theme/        # light/dark theme context
```

Design tokens (colors, fonts) live as CSS custom properties in `src/index.css` and are mapped into Tailwind via `@theme`, with a `.light` class override for light mode.

## Backend

This frontend expects a FastAPI backend exposing endpoints under `/auth`, `/resume`, `/job-description`, `/matching`, `/recommendations`, `/skill-assessment`, `/interview`, `/roadmap`, `/resume-builder`, `/documents`, and `/admin`. See the backend repository for setup instructions.
