from fastapi import FastAPI
from app.routes import resume, auth, job_description, matching
from app.database import engine, Base
from app.models import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ResumeIQ API")

app.include_router(resume.router)
app.include_router(auth.router)
app.include_router(job_description.router)
app.include_router(matching.router)


@app.get("/")
def read_root():
    return {"message": "ResumeIQ API is running"}