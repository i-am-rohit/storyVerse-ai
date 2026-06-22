import io
import re
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile


class DocumentParseError(Exception):
    pass


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_upload(upload: UploadedFile) -> str:
    ext = Path(upload.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentParseError("Unsupported file type. Please upload PDF, DOCX, or TXT.")
    if upload.size > MAX_FILE_SIZE:
        raise DocumentParseError("File exceeds the 10 MB size limit.")
    return ext.lstrip(".")


def extract_text(upload: UploadedFile, file_type: str) -> tuple[str, int]:
    if file_type == "txt":
        return _extract_txt(upload)
    if file_type == "pdf":
        return _extract_pdf(upload)
    if file_type == "docx":
        return _extract_docx(upload)
    raise DocumentParseError(f"Unsupported file type: {file_type}")


def _extract_txt(upload: UploadedFile) -> tuple[str, int]:
    raw = upload.read()
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise DocumentParseError("Could not decode text file.")
    return _clean_text(text), 1


def _extract_pdf(upload: UploadedFile) -> tuple[str, int]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentParseError("PDF support is not installed.") from exc

    reader = PdfReader(io.BytesIO(upload.read()))
    pages = []
    for page in reader.pages:
        content = page.extract_text()
        if content:
            pages.append(content)
    if not pages:
        raise DocumentParseError("No readable text found in the PDF.")
    return _clean_text("\n\n".join(pages)), len(reader.pages)


def _extract_docx(upload: UploadedFile) -> tuple[str, int]:
    try:
        from docx import Document
    except ImportError as exc:
        raise DocumentParseError("DOCX support is not installed.") from exc

    doc = Document(io.BytesIO(upload.read()))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        raise DocumentParseError("No readable text found in the DOCX file.")
    return _clean_text("\n\n".join(paragraphs)), max(1, len(paragraphs) // 20)


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()
