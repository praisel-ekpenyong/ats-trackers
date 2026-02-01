from __future__ import annotations

import io
from pathlib import Path
from typing import Tuple

import pdfplumber
from docx import Document


def read_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def read_pdf(file_bytes: bytes) -> Tuple[str, str | None]:
    text_chunks: list[str] = []
    warning = None
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)
    text = "\n".join(text_chunks).strip()
    if len(text) < 50:
        warning = "PDF text extraction returned very little text. This PDF may be scanned."
    return text, warning


def read_docx(file_bytes: bytes) -> str:
    document = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in document.paragraphs]
    return "\n".join(paragraphs).strip()


def read_file(file_path: Path) -> Tuple[str, str | None]:
    suffix = file_path.suffix.lower()
    file_bytes = file_path.read_bytes()
    if suffix == ".pdf":
        return read_pdf(file_bytes)
    if suffix == ".docx":
        return read_docx(file_bytes), None
    return read_txt(file_bytes), None


def read_upload(file_name: str, file_bytes: bytes) -> Tuple[str, str | None]:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".pdf":
        return read_pdf(file_bytes)
    if suffix == ".docx":
        return read_docx(file_bytes), None
    return read_txt(file_bytes), None
