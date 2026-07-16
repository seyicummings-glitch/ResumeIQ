from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.resume_parser import extract_resume_text
from app.services.resume_structurer import structure_resume

router = APIRouter(prefix="/resume", tags=["Resume"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_file(file: UploadFile, file_bytes: bytes):
    filename = file.filename.lower()
    file_extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_extension}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
        )


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes)

        text = extract_resume_text(file.filename, file_bytes)
        return {
            "filename": file.filename,
            "extracted_text_preview": text[:500],
            "character_count": len(text)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/structure")
async def structure_resume_endpoint(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        validate_file(file, file_bytes)

        text = extract_resume_text(file.filename, file_bytes)
        structured_data = structure_resume(text)
        return {
            "filename": file.filename,
            "structured_data": structured_data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error structuring resume: {str(e)}")