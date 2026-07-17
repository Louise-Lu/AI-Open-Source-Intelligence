"""Layer 1 — Intent Understanding evaluator (multi-label)."""

from __future__ import annotations

from typing import Any

from evaluation.metrics import f1_score, precision, recall


def _expected_intents(item: dict[str, Any]) -> list[str]:
    if "expected_intents" in item:
        return list(item.get("expected_intents") or [])
    # Backward compatibility with legacy single-label field.
    legacy = item.get("intent")
    if isinstance(legacy, str) and legacy:
        return [legacy]
    if isinstance(legacy, list):
        return list(legacy)
    return []


def evaluate_intent(
    item: dict[str, Any],
    predicted_intents: list[str],
) -> dict[str, Any]:
    """
    Evaluate multi-label intent classification.

    Precision = |predicted ∩ expected| / |predicted|
    Recall    = |predicted ∩ expected| / |expected|
    F1        = 2 * P * R / (P + R)
    """
    expected_list = _expected_intents(item)
    predicted_list = list(predicted_intents or [])

    expected_set = set(expected_list)
    predicted_set = set(predicted_list)

    prec = precision(predicted_set, expected_set)
    rec = recall(predicted_set, expected_set)
    f1 = f1_score(prec, rec)

    return {
        "layer": "intent",
        "implemented": True,
        "score": {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            # 0–100 scale for report / per-item intent_score
            "intent_score": round(f1 * 100),
        },
        "details": {
            "expected_intents": expected_list,
            "predicted_intents": predicted_list,
            "correct_intents": sorted(expected_set & predicted_set),
            "missed_intents": sorted(expected_set - predicted_set),
            "extra_intents": sorted(predicted_set - expected_set),
        },
    }
