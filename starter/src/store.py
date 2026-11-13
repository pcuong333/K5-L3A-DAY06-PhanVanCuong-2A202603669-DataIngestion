"""Persist and search chunks with PostgreSQL + pgvector."""
import math
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        if not database_url.strip():
            raise ValueError("database_url must not be empty")
        self.database_url = database_url
        self.dimensions = dimensions

    def create_schema(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS ingestion_chunks (
                        strategy TEXT NOT NULL,
                        chunk_id TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.dimensions}) NOT NULL,
                        PRIMARY KEY (strategy, chunk_id)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS ingestion_chunks_metadata_idx
                    ON ingestion_chunks USING GIN (metadata)
                    """
                )

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Replace one strategy's rows atomically and remove obsolete chunks.

        Replacing the strategy makes repeated ingestion deterministic and removes
        chunks that disappeared after a source document changed.
        """
        if not strategy.strip():
            raise ValueError("strategy must not be empty")
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        for vector in vectors:
            self._validate_vector(vector)

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM ingestion_chunks WHERE strategy = %s",
                    (strategy,),
                )
                for chunk, vector in zip(chunks, vectors):
                    cursor.execute(
                        """
                        INSERT INTO ingestion_chunks
                            (strategy, chunk_id, document_id, source, page, text, metadata, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                        """,
                        (
                            strategy,
                            chunk.chunk_id,
                            chunk.document_id,
                            chunk.source,
                            chunk.page,
                            chunk.text,
                            Jsonb(chunk.metadata),
                            _vector_literal(vector),
                        ),
                    )

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return nearest chunks ranked by cosine similarity.

        Filters use JSONB containment, so values must match stored metadata exactly.
        """
        if not strategy.strip():
            raise ValueError("strategy must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        self._validate_vector(query_vector)

        filter_clause = ""
        parameters: list[Any] = [_vector_literal(query_vector), strategy]
        if filters:
            filter_clause = "AND metadata @> %s::jsonb"
            parameters.append(Jsonb(filters))
        parameters.extend([_vector_literal(query_vector), top_k])

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT chunk_id, document_id, source, page, text, metadata,
                           1 - (embedding <=> %s::vector) AS score
                    FROM ingestion_chunks
                    WHERE strategy = %s {filter_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    parameters,
                )
                return [
                    {
                        "chunk_id": row[0],
                        "text": row[4],
                        "metadata": {
                            **(row[5] or {}),
                            "document_id": row[1],
                            "source": row[2],
                            "page": row[3],
                        },
                        "score": float(row[6]),
                    }
                    for row in cursor.fetchall()
                ]

    def _validate_vector(self, vector: list[float]) -> None:
        if len(vector) != self.dimensions:
            raise ValueError(
                f"vector dimension {len(vector)} does not match model dimension {self.dimensions}"
            )
        if not all(math.isfinite(float(value)) for value in vector):
            raise ValueError("vector values must be finite")


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"
