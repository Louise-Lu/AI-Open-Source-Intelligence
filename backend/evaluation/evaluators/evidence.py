"""Layer 3 — Evidence Quality evaluator (interface only, Phase 1)."""

from __future__ import annotations

from typing import Any


def evaluate_evidence(
    item: dict[str, Any],
    answer: str,
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Placeholder for Evidence Quality.

    Future checks:
    - Evidence Completeness
    - Evidence Relevance
    - Evidence Freshness
    - whether evidence is sufficient to support the answer
    """
    return {
        "layer": "evidence",
        "implemented": False,
        "score": None,
        "details": {
            "trace_steps": len(trace or []),
            "note": "Evidence evaluator not implemented in Phase 1.",
        },
    }
