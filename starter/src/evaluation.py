"""Evaluate retrieval evidence and preserve per-query traces."""
import re
from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check gold source/page and evidence presence for one query."""
    gold_source = question["gold_source_id"]
    gold_page = question["gold_page"]
    evidence = _normalize(question["evidence_quote"])
    checked_hits: list[dict[str, Any]] = []

    for hit in hits:
        metadata = hit.get("metadata") or {}
        source_page_hit = (
            metadata.get("document_id") == gold_source
            and metadata.get("page") == gold_page
        )
        contains_evidence = evidence in _normalize(hit.get("text", ""))
        checked_hits.append(
            {
                **hit,
                "source_page_hit": source_page_hit,
                "contains_evidence": contains_evidence,
                "evidence_hit": source_page_hit and contains_evidence,
            }
        )

    return {
        "question_id": question["id"],
        "split": question["split"],
        "question": question["question"],
        "hits": checked_hits,
        "hit_at_1": bool(checked_hits and checked_hits[0]["evidence_hit"]),
        "evidence_hit_at_3": any(hit["evidence_hit"] for hit in checked_hits[:3]),
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and split."""
    summary: dict[str, Any] = {}
    for trace in traces:
        key = f"{trace['strategy']}:{trace['split']}"
        bucket = summary.setdefault(
            key,
            {
                "strategy": trace["strategy"],
                "split": trace["split"],
                "n": 0,
                "hit_at_1": 0,
                "evidence_hit_at_3": 0,
            },
        )
        bucket["n"] += 1
        bucket["hit_at_1"] += int(trace["hit_at_1"])
        bucket["evidence_hit_at_3"] += int(trace["evidence_hit_at_3"])
    return summary


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
