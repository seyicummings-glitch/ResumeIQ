# -ResumeIQ
AI Resume Analyzer

## Deployment / HTTPS

The app itself only redirects http→https and adds an HSTS header when the `FORCE_HTTPS` env var is set to `true`. Real TLS certificates are provisioned outside this repo — at a reverse proxy (Nginx/Caddy + Let's Encrypt) or a hosting platform's managed HTTPS. Only set `FORCE_HTTPS=true` once that upstream TLS termination is actually in place; otherwise it just breaks plain-http access with nothing to redirect to.
