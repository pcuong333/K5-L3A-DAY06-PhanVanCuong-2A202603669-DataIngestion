"""Read and normalize source data."""
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical PDF page while preserving traceability.

    Page numbers are one-based physical page numbers. OCR is intentionally not
    performed here; pages with no extractable text are returned with a warning
    in their metadata so a later OCR step can handle them explicitly.
    """
    reader = PdfReader(str(path))
    pages: list[DocumentPage] = []

    for page_number, pdf_page in enumerate(reader.pages, start=1):
        raw_text = pdf_page.extract_text() or ""
        text = normalize_text(raw_text)
        metadata: dict[str, object] = {
            "text_extraction": "ok" if text else "empty",
        }
        if not text:
            metadata["warning"] = "No extractable text; OCR may be required."

        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_number,
                text=text,
                metadata=metadata,
            )
        )

    return pages


def normalize_text(text: str) -> str:
    """Normalize Unicode and horizontal whitespace while retaining paragraphs."""
    normalized = unicodedata.normalize("NFKC", text).replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()
