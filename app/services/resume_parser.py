import os
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
import io
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

load_dotenv()

# Path to Tesseract executable — override via TESSERACT_CMD env var for non-default installs
pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Path to Poppler bin folder — override via POPPLER_PATH env var
POPPLER_PATH = os.getenv(
    "POPPLER_PATH", r"C:\poppler\poppler-26.02.0\Library\bin"
)

# Combine all installed languages so Tesseract can detect and read any of them
OCR_LANGUAGES = "eng+fra+spa+deu+por+ara+chi_sim+hin+rus+ita+tur"


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
        text += pytesseract.image_to_string(image, lang=OCR_LANGUAGES) + "\n"
    return text


def _iter_block_items(document):
    """Yields paragraphs and tables in the order they actually appear in the
    document body. python-docx's `document.paragraphs` only returns top-level
    paragraphs and silently skips anything inside a table — but many resume
    templates put contact info (phone, LinkedIn) or a skills list inside a
    table/sidebar layout, so that content would otherwise never be extracted
    at all, regardless of what parsing runs on the text afterward."""
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    lines = []

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            if block.text.strip():
                lines.append(block.text)
        else:
            for row in block.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        lines.append(cell.text)

    return "\n".join(lines)


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
        return pytesseract.image_to_string(image, lang=OCR_LANGUAGES)
    else:
        raise ValueError("Unsupported file type. Please upload PDF, DOCX, TXT, PNG, or JPG.")