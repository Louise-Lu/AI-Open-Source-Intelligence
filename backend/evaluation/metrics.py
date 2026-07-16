"""Shared metric helpers for the evaluation pipeline."""

from __future__ import annotations


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def precision(predicted: set[str], expected: set[str]) -> float:
    """Precision = |predicted ∩ expected| / |predicted|."""
    if not predicted:
        return 1.0 if not expected else 0.0
    return safe_div(len(predicted & expected), len(predicted))


def recall(predicted: set[str], expected: set[str]) -> float:
    """Recall = |predicted ∩ expected| / |expected|."""
    if not expected:
        return 1.0
    return safe_div(len(predicted & expected), len(expected))


def f1_score(prec: float, rec: float) -> float:
    return safe_div(2 * prec * rec, prec + rec)


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"
