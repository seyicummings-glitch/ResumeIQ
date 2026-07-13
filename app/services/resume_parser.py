from pypdf import PdfReader
from docx import Document
import io
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Path to Poppler bin folder
POPPLER_PATH = r"C:\poppler\poppler-26.02.0\Library\bin"


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    # If normal extraction returns little/no text, it's likely a scanned PDF — use OCR
    if len(text.strip()) < 30:
        text = extract_text_with_ocr(file_bytes)

    return text


def extract_text_with_ocr(file_bytes: bytes) -> str:
    images = convert_from_bytes(file_bytes, poppler_path=POPPLER_PATH)
    text = ""
    for image in images:
        text += pytesseract.image_to_string(image) + "\n"
    return text


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    text = "\n".join([para.text for para in doc.paragraphs])
    return text


def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def extract_resume_text(filename: str, file_bytes: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename.lower().endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif filename.lower().endswith(".txt"):
        return extract_text_from_txt(file_bytes)
    elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)
    else:
        raise ValueError("Unsupported file type. Please upload PDF, DOCX, TXT, PNG, or JPG.")