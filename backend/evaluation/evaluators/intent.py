"""Layer 1 — Intent Understanding evaluator (interface only, Phase 1)."""

from __future__ import annotations

from typing import Any


def evaluate_intent(
    item: dict[str, Any],
    answer: str,
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Placeholder for Intent Understanding.

    Future checks:
    - correct understanding of the user question
    - correct repository identification
    - correct task / intent type
    """
    return {
        "layer": "intent",
        "implemented": False,
        "score": None,
        "details": {
            "expected_intent": item.get("intent"),
            "expected_repo": item.get("repo"),
            "note": "Intent evaluator not implemented in Phase 1.",
        },
    }
