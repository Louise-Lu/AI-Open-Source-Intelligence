"""Layer 3 — Evidence Quality evaluator (rule-based, Phase 2)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


FRESH_DAYS = 180
STALE_DAYS = 365

WEIGHT_COMPLETENESS = 0.50
WEIGHT_FRESHNESS = 0.20
WEIGHT_COVERAGE = 0.30


def evaluate_evidence(
    item: dict[str, Any],
    evidence: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    """
    Rule-based Evidence Quality scoring.

    Dimensions:
    - Completeness (50%): required_evidence present?
    - Freshness (20%): recent timestamps in evidence?
    - Coverage (30%): answer length / empty evidence / unsupported claims
    """
    evidence = evidence or {}
    required = list(item.get("required_evidence") or [])

    completeness, missing = _score_completeness(required, evidence)
    freshness, freshness_details = _score_freshness(evidence)
    coverage, coverage_details = _score_coverage(answer or "", evidence, item)

    score = round(
        completeness * WEIGHT_COMPLETENESS
        + freshness * WEIGHT_FRESHNESS
        + coverage * WEIGHT_COVERAGE
    )

    return {
        "layer": "evidence",
        "implemented": True,
        "score": score,
        "details": {
            "completeness": round(completeness),
            "freshness": round(freshness),
            "coverage": round(coverage),
            "missing_evidence": missing,
            "freshness_details": freshness_details,
            "coverage_details": coverage_details,
            "required_evidence": required,
        },
    }


def _path_value(evidence: dict[str, Any], path: str) -> Any:
    current: Any = evidence
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    # numbers (including 0) and bools count as present
    return True


def _score_completeness(
    required: list[str],
    evidence: dict[str, Any],
) -> tuple[float, list[str]]:
    if not required:
        return 100.0, []

    missing: list[str] = []
    for path in required:
        if not _is_present(_path_value(evidence, path)):
            missing.append(path)

    present_count = len(required) - len(missing)
    score = 100.0 * present_count / len(required)
    return score, missing


def _parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _collect_timestamps(evidence: dict[str, Any]) -> list[datetime]:
    timestamps: list[datetime] = []

    repo = evidence.get("repository") or {}
    if isinstance(repo, dict):
        for key in ("updated_at", "created_at", "pushed_at"):
            dt = _parse_datetime(repo.get(key))
            if dt:
                timestamps.append(dt)

    for release in evidence.get("releases") or []:
        if isinstance(release, dict):
            dt = _parse_datetime(release.get("published_at"))
            if dt:
                timestamps.append(dt)

    for issue in evidence.get("issues") or []:
        if isinstance(issue, dict):
            dt = _parse_datetime(issue.get("created_at"))
            if dt:
                timestamps.append(dt)

    for pr in evidence.get("pull_requests") or []:
        if isinstance(pr, dict):
            dt = _parse_datetime(pr.get("created_at"))
            if dt:
                timestamps.append(dt)

    return timestamps


def _score_freshness(evidence: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    timestamps = _collect_timestamps(evidence)
    if not timestamps:
        return 40.0, {
            "status": "missing",
            "newest": None,
            "note": "No timestamp fields found in evidence.",
        }

    now = datetime.now(timezone.utc)
    newest = max(timestamps)
    age_days = max(0.0, (now - newest).total_seconds() / 86400.0)

    if age_days <= FRESH_DAYS:
        score = 100.0
        status = "fresh"
    elif age_days <= STALE_DAYS:
        # Linear decay from 100 at 180d to 60 at 365d
        ratio = (age_days - FRESH_DAYS) / (STALE_DAYS - FRESH_DAYS)
        score = 100.0 - ratio * 40.0
        status = "aging"
    else:
        score = 40.0
        status = "stale"

    return score, {
        "status": status,
        "newest": newest.isoformat(),
        "age_days": round(age_days, 1),
        "timestamp_count": len(timestamps),
    }


def _flatten_evidence_text(evidence: dict[str, Any]) -> str:
    chunks: list[str] = []

    def walk(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        else:
            chunks.append(str(value))

    walk(evidence)
    return " ".join(chunks).lower()


def _score_coverage(
    answer: str,
    evidence: dict[str, Any],
    item: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    answer = answer or ""
    answer_len = len(answer.strip())
    evidence_text = _flatten_evidence_text(evidence)
    has_any_evidence = bool(evidence_text.strip())

    # Base from answer length (thin answers score lower)
    if answer_len == 0:
        length_score = 0.0
    elif answer_len < 80:
        length_score = 55.0
    elif answer_len < 200:
        length_score = 75.0
    else:
        length_score = 90.0

    empty_penalty = 0.0 if has_any_evidence else 35.0

    unsupported = _find_unsupported_claims(answer, evidence, evidence_text)
    unsupported_penalty = min(40.0, len(unsupported) * 10.0)

    score = max(0.0, length_score - empty_penalty - unsupported_penalty)
    return score, {
        "answer_length": answer_len,
        "evidence_empty": not has_any_evidence,
        "unsupported_claims": unsupported,
        "unsupported_count": len(unsupported),
        "expected_intents": item.get("expected_intents") or (
            [item["intent"]] if item.get("intent") else []
        ),
    }


def _find_unsupported_claims(
    answer: str,
    evidence: dict[str, Any],
    evidence_text: str,
) -> list[str]:
    """
    Lightweight unsupported-claim heuristics (no embeddings).
    """
    unsupported: list[str] = []
    lower = answer.lower()

    # Numeric claims in the answer should appear in evidence when evidence exists.
    numbers = re.findall(r"\b\d{2,}\b", answer.replace(",", ""))
    if evidence_text:
        for number in numbers[:8]:
            if number not in evidence_text.replace(",", ""):
                # Skip common non-evidence numbers (years already in evidence often)
                if number.startswith("20") and len(number) == 4:
                    continue
                unsupported.append(f"number:{number}")

    repo = evidence.get("repository") if isinstance(evidence.get("repository"), dict) else {}

    claim_checks = [
        ("star", "repository.stars", repo.get("stars")),
        ("fork", "repository.forks", repo.get("forks")),
        ("license", "repository.license", repo.get("license")),
        ("language", "repository.language", repo.get("language")),
    ]
    for keyword, label, value in claim_checks:
        if keyword in lower and not _is_present(value):
            # Only flag if answer strongly asserts the attribute
            if re.search(rf"\b{keyword}s?\b", lower):
                unsupported.append(label)

    if re.search(r"\b(readme|documentation|docs)\b", lower) and not _is_present(
        evidence.get("readme")
    ):
        unsupported.append("readme")

    if re.search(r"\b(release|version|changelog)\b", lower) and not _is_present(
        evidence.get("releases")
    ):
        unsupported.append("releases")

    if re.search(r"\b(issue|bug|ticket)\b", lower) and not _is_present(evidence.get("issues")):
        unsupported.append("issues")

    if re.search(r"\b(pull request|pr\b|merge request)\b", lower) and not _is_present(
        evidence.get("pull_requests")
    ):
        unsupported.append("pull_requests")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for claim in unsupported:
        if claim not in seen:
            seen.add(claim)
            unique.append(claim)
    return unique
