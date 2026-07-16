from fastapi import APIRouter
from pydantic import BaseModel
from app.services.job_description_parser import parse_job_description

router = APIRouter(prefix="/job-description", tags=["Job Description"])


class JobDescriptionInput(BaseModel):
    content: str


@router.post("/parse")
def parse_jd(data: JobDescriptionInput):
    result = parse_job_description(data.content)
    return result