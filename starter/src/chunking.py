"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split a page into deterministic overlapping character windows."""
    if size <= 0:
        raise ValueError("size must be greater than zero")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be between zero and size - 1")
    if not page.text:
        return []

    chunks: list[Chunk] = []
    step = size - overlap
    for index, start in enumerate(range(0, len(page.text), step)):
        text = page.text[start : start + size].strip()
        if not text:
            continue
        metadata = _chunk_metadata(page, "fixed", index)
        metadata.update({"char_start": start, "char_end": min(start + size, len(page.text))})
        chunks.append(
            Chunk(
                chunk_id=f"{page.document_id}-p{page.page}-fixed-{index}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=text,
                metadata=metadata,
            )
        )
    return chunks


def by_paragraph(page: DocumentPage, max_size: int = 500) -> list[Chunk]:
    """Group paragraphs up to ``max_size`` and split oversized paragraphs."""
    if max_size <= 0:
        raise ValueError("max_size must be greater than zero")
    if not page.text:
        return []

    paragraphs = [paragraph.strip() for paragraph in page.text.split("\n\n") if paragraph.strip()]
    chunks: list[Chunk] = []
    pending = ""

    def add_chunk(text: str) -> None:
        index = len(chunks)
        chunks.append(
            Chunk(
                chunk_id=f"{page.document_id}-p{page.page}-paragraph-{index}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=text,
                metadata=_chunk_metadata(page, "paragraph", index),
            )
        )

    for paragraph in paragraphs:
        if len(paragraph) > max_size:
            if pending:
                add_chunk(pending)
                pending = ""
            for start in range(0, len(paragraph), max_size):
                add_chunk(paragraph[start : start + max_size].strip())
            continue

        candidate = f"{pending}\n\n{paragraph}" if pending else paragraph
        if len(candidate) <= max_size:
            pending = candidate
        else:
            add_chunk(pending)
            pending = paragraph

    if pending:
        add_chunk(pending)
    return chunks


def _chunk_metadata(page: DocumentPage, strategy: str, index: int) -> dict[str, object]:
    metadata = dict(page.metadata)
    metadata.update({"chunking_strategy": strategy, "chunk_index": index})
    return metadata
