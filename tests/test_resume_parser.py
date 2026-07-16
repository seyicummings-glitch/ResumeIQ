import pytest
from app.services.resume_parser import extract_resume_text


def test_extract_text_from_txt():
    file_bytes = b"John Doe\nSoftware Engineer\nPython, FastAPI, PostgreSQL"
    result = extract_resume_text("resume.txt", file_bytes)
    assert "John Doe" in result
    assert "Python" in result


def test_unsupported_file_type_raises_error():
    file_bytes = b"some content"
    with pytest.raises(ValueError):
        extract_resume_text("resume.xyz", file_bytes)


def test_empty_txt_file():
    file_bytes = b""
    result = extract_resume_text("resume.txt", file_bytes)
    assert result == ""