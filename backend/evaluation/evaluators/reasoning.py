"""Layer 4 — Reasoning Quality evaluator (interface only, Phase 1)."""

from __future__ import annotations

from typing import Any


def evaluate_reasoning(
    item: dict[str, Any],
    answer: str,
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Placeholder for Reasoning Quality.

    Future checks (Evidence → Reasoning → Conclusion):
    - Logical Consistency
    - Grounded Reasoning
    - Unsupported Claims
    - Hallucination
    """
    return {
        "layer": "reasoning",
        "implemented": False,
        "score": None,
        "details": {
            "answer_length": len(answer or ""),
            "note": "Reasoning evaluator not implemented in Phase 1.",
        },
    }
