"""Run the ingestion and retrieval benchmark."""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .store import PgVectorStore


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "data" / "introduction_to_computer_science.pdf"
QUESTIONS_PATH = ROOT / "benchmark" / "questions.json"
RESULTS_PATH = ROOT / "results"


def main() -> None:
    load_dotenv(ROOT / ".env")
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Corpus not found: {PDF_PATH}")
    if not QUESTIONS_PATH.exists():
        raise FileNotFoundError(f"Benchmark not found: {QUESTIONS_PATH}")

    with QUESTIONS_PATH.open(encoding="utf-8") as file:
        questions = json.load(file)
    if len(questions) < 20:
        raise ValueError("Benchmark must contain at least 20 questions")

    all_pages = load_pdf(PDF_PATH, "openstax_cs", str(PDF_PATH))
    pages = [page for page in all_pages if 30 <= page.page <= 80 and page.text]
    if len(pages) < 30:
        raise ValueError(f"Selected corpus has only {len(pages)} readable pages")
    for page in pages:
        page.metadata["section"] = _section_for_page(page.page)

    model_name = os.getenv("EMBEDDING_MODEL") or None
    embedder = MyEmbedder(model_name) if model_name else MyEmbedder()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required in starter/.env")
    store = PgVectorStore(database_url, embedder.dimensions)
    store.create_schema()

    strategies = {
        "A": [chunk for page in pages for chunk in fixed_size(page, 800, 100)],
        "B": [chunk for page in pages for chunk in by_paragraph(page, 800)],
    }
    strategies["C"] = strategies["B"]
    traces: list[dict[str, object]] = []

    for strategy, chunks in strategies.items():
        started = time.perf_counter()
        vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        store.upsert(strategy, chunks, vectors)
        ingest_seconds = time.perf_counter() - started
        for question in questions:
            query_vector = embedder.embed_query(question["question"])
            filters = question.get("filter") if strategy == "C" else None
            hits = store.search(strategy, query_vector, top_k=3, filters=filters)
            trace = evaluate_query(question, hits)
            trace.update(
                {
                    "strategy": strategy,
                    "ingest_seconds": round(ingest_seconds, 4),
                    "chunk_count": len(chunks),
                    "filter": filters,
                }
            )
            traces.append(trace)

    RESULTS_PATH.mkdir(exist_ok=True)
    (RESULTS_PATH / "traces.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RESULTS_PATH / "summary.json").write_text(
        json.dumps(summarize(traces), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Completed benchmark: {len(traces)} traces")


def _section_for_page(page: int) -> str:
    if page <= 48:
        return "Introduction to Computer Science"
    if page <= 61:
        return "Computational Thinking"
    return "Architecting Solutions with Adaptive Design Reuse in Mind"


if __name__ == "__main__":
    main()
