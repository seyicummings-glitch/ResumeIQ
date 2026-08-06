import os
from fastapi import FastAPI
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import JSONResponse
from app.routes import resume, auth, job_description, matching, github_analyzer, recommendations, health, documents, skill_assessment, interview, roadmap, resume_builder, admin
from app.database import engine, Base, SessionLocal
from app.models import models, document_models, skill_assessment_models, roadmap_models, admin_models, interview_models
from app.models.admin_models import AppSetting
from app.services.rate_limiter import is_rate_limited

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ResumeIQ API")

FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() == "true"

if FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

    @app.middleware("http")
    async def add_hsts_header(request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

# MAINTENANCE_MODE env var is a hard override that works even if the database
# itself is unreachable. Otherwise, maintenance mode and the rate limit are
# both read live from the AppSetting row on every request, so the Admin
# Settings page (PUT /admin/settings) actually takes effect without
# restarting the app.
FORCE_MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

# /health always stays up for uptime monitors; /auth and /admin stay reachable
# during maintenance so an admin can still log in and turn it back off.
MAINTENANCE_EXEMPT_PREFIXES = ("/health", "/auth", "/admin")


@app.middleware("http")
async def platform_settings_guard(request, call_next):
    path = request.url.path
    if path == "/health":
        return await call_next(request)

    db = SessionLocal()
    try:
        setting = db.query(AppSetting).first()
    finally:
        db.close()

    support_contact = f" Contact {setting.support_email} for help." if setting and setting.support_email else ""

    maintenance_active = FORCE_MAINTENANCE_MODE or bool(setting and setting.maintenance_mode)
    if maintenance_active and not path.startswith(MAINTENANCE_EXEMPT_PREFIXES):
        return JSONResponse(
            status_code=503,
            content={"detail": f"Service is under scheduled maintenance.{support_contact}"},
        )

    rate_limit = setting.rate_limit_per_minute if setting else 60
    client_id = request.client.host if request.client else "unknown"
    if is_rate_limited(client_id, rate_limit):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Too many requests. Please slow down and try again shortly.{support_contact}"},
        )

    return await call_next(request)

app.include_router(resume.router)
app.include_router(auth.router)
app.include_router(job_description.router)
app.include_router(matching.router)
app.include_router(github_analyzer.router)
app.include_router(recommendations.router)
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(skill_assessment.router)
app.include_router(interview.router)
app.include_router(roadmap.router)
app.include_router(resume_builder.router)
app.include_router(admin.router)
app.include_router(admin.reports_router)


@app.get("/")
def read_root():
    return {"message": "ResumeIQ API is running"}