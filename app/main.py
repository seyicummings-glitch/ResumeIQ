from fastapi import FastAPI

app = FastAPI(title="ResumeIQ API")

@app.get("/")
def read_root():
    return {"message": "ResumeIQ API is running"}