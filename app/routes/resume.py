from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.resume_parser import extract_resume_text
from app.services.resume_structurer import structure_resume

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        text = extract_resume_text(file.filename, file_bytes)
        return {
            "filename": file.filename,
            "extracted_text_preview": text[:500],
            "character_count": len(text)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/structure")
async def structure_resume_endpoint(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        text = extract_resume_text(file.filename, file_bytes)
        structured_data = structure_resume(text)
        return {
            "filename": file.filename,
            "structured_data": structured_data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error structuring resume: {str(e)}")