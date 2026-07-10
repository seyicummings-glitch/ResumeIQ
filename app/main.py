from fastapi import FastAPI
from app.routes import resume

app = FastAPI(title="ResumeIQ API")

app.include_router(resume.router)


@app.get("/")
def read_root():
    return {"message": "ResumeIQ API is running"}