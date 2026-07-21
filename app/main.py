import os
from fastapi import FastAPI
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from app.routes import resume, auth, job_description, matching, github_analyzer, recommendations
from app.database import engine, Base
from app.models import models

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

app.include_router(resume.router)
app.include_router(auth.router)
app.include_router(job_description.router)
app.include_router(matching.router)
app.include_router(github_analyzer.router)
app.include_router(recommendations.router)


@app.get("/")
def read_root():
    return {"message": "ResumeIQ API is running"}