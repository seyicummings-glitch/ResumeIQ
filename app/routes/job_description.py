from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from app.services.job_description_parser import parse_job_description
from app.services.resume_parser import extract_resume_text

router = APIRouter(prefix="/job-description", tags=["Job Description"])


class JobDescriptionInput(BaseModel):
    content: str


@router.post("/parse")
def parse_jd_text(data: JobDescriptionInput):
    result = parse_job_description(data.content)
    return {"source": "text", "job_description_analysis": result}


@router.post("/parse-file")
async def parse_jd_file(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        text = extract_resume_text(file.filename, file_bytes)
        result = parse_job_description(text)
        return {
            "source": "file",
            "filename": file.filename,
            "extracted_text_preview": text[:500],
            "job_description_analysis": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


class JobDescriptionURLInput(BaseModel):
    url: str


@router.post("/parse-url")
def parse_jd_url(data: JobDescriptionURLInput):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(data.url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        if len(text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract meaningful content from this URL.")

        result = parse_job_description(text)
        return {
            "source": "url",
            "url": data.url,
            "extracted_text_preview": text[:500],
            "job_description_analysis": result
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing URL: {str(e)}")