"""Layer 4 — Reasoning Quality evaluator (rule-based, Phase 1)."""

from __future__ import annotations

import re
from typing import Any


WEIGHT_GROUNDING = 0.50
WEIGHT_CONTRADICTION = 0.30
WEIGHT_COMPLETENESS = 0.20

# Relative tolerance for numeric contradiction (e.g. 37k vs 37000).
NUMERIC_REL_TOLERANCE = 0.15
NUMERIC_ABS_TOLERANCE = 5

INTENT_KEYWORDS: dict[str, list[str]] = {
    "repository": ["star", "fork", "language", "license", "topic", "repository", "repo"],
    "readme": ["readme", "document", "docs", "getting started", "overview", "describe"],
    "release": ["release", "version", "tag", "changelog", "published"],
    "issue": ["issue", "bug", "ticket", "open", "report"],
    "pr": ["pull request", "pr", "merge", "pull"],
    "project_overview": ["is", "project", "framework", "library", "overview", "about"],
    "project_health": ["health", "active", "maintain", "community", "activity", "healthy"],
    "roadmap": ["roadmap", "future", "direction", "heading", "upcoming", "next"],
    "recommendation": ["recommend", "suitable", "should", "adopt", "enterprise", "production"],
    "comparison": ["compare", "versus", "vs", "than", "both", "difference"],
}


def evaluate_reasoning(
    item: dict[str, Any],
    evidence: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    """
    Rule-based Reasoning Quality scoring.

    Dimensions:
    - Evidence Grounding (50%)
    - Contradiction Detection (30%)
    - Reasoning Completeness (20%)
    """
    evidence = evidence or {}
    answer = answer or ""

    grounding, unsupported = _score_grounding(answer, evidence, item)
    contradictions_score, contradictions = _score_contradictions(answer, evidence, item)
    completeness = _score_completeness(item, answer, evidence)

    score = round(
        grounding * WEIGHT_GROUNDING
        + contradictions_score * WEIGHT_CONTRADICTION
        + completeness * WEIGHT_COMPLETENESS
    )

    return {
        "layer": "reasoning",
        "implemented": True,
        "score": score,
        "details": {
            "grounding": round(grounding),
            "contradictions": round(contradictions_score),
            "completeness": round(completeness),
            "unsupported_claims": unsupported,
            "contradiction_list": contradictions,
        },
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


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _repo(evidence: dict[str, Any]) -> dict[str, Any]:
    repo = evidence.get("repository")
    return repo if isinstance(repo, dict) else {}


def _normalize_number_token(token: str) -> int | None:
    text = token.lower().replace(",", "").strip()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([kmb])?", text)
    if not match:
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits.isdigit() else None

    value = float(match.group(1))
    suffix = match.group(2)
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    elif suffix == "b":
        value *= 1_000_000_000
    return int(value)


def _numbers_close(a: int, b: int) -> bool:
    if a == b:
        return True
    diff = abs(a - b)
    if diff <= NUMERIC_ABS_TOLERANCE:
        return True
    base = max(abs(a), abs(b), 1)
    return (diff / base) <= NUMERIC_REL_TOLERANCE


def _explicit_metric_numbers(text: str, metric: str) -> list[int]:
    """
    Extract numbers explicitly tied to a metric, e.g.:
    - 37,419 stars
    - stars: 37419
    - ~25k forks
    """
    patterns = [
        rf"(\d[\d,]*(?:\.\d+)?[kmbKMB]?)\s*\+?\s*{metric}s?\b",
        rf"\b{metric}s?\s*[:=]?\s*(\d[\d,]*(?:\.\d+)?[kmbKMB]?)",
    ]
    found: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            number = _normalize_number_token(match.group(1))
            if number is not None:
                found.append(number)
    return found


def _sentence_windows(text: str) -> list[str]:
    parts = re.split(r"(?<=[\.!\?\n])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _explicit_metric_numbers_for_target(
    text: str,
    metric: str,
    target_repo: str,
) -> list[int]:
    """
    Prefer metric claims about the target repository.
    In comparison answers, ignore 'AutoGPT has 168k stars' when target is langgraph.
    """
    selected: list[int] = []
    generic: list[int] = []

    for sentence in _sentence_windows(text):
        numbers = _explicit_metric_numbers(sentence, metric)
        if not numbers:
            continue
        lower = sentence.lower()
        if target_repo and target_repo in lower:
            selected.extend(numbers)
            continue

        # Generic evidence-style lines: "Stars: 37419" / "- Stars 37k"
        if re.search(
            rf"^\s*[-*]?\s*\*{{0,2}}{metric}s?\*{{0,2}}\s*[:=]",
            sentence,
            flags=re.IGNORECASE,
        ):
            generic.extend(numbers)

    if selected:
        return selected
    if generic:
        return generic
    # Last resort for short direct answers without repo name.
    if not target_repo:
        return _explicit_metric_numbers(text, metric)
    # If answer is short and only mentions one metric claim, keep it.
    all_claims = _explicit_metric_numbers(text, metric)
    if len(set(all_claims)) == 1 and len(text) < 280:
        return all_claims
    return []


def _score_grounding(
    answer: str,
    evidence: dict[str, Any],
    item: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
    """
    Check whether answer claims are grounded in evidence.
    Empty answer or empty evidence both lower the score.
    """
    unsupported: list[str] = []
    lower = answer.lower()
    evidence_text = _flatten_evidence_text(evidence)
    has_evidence = bool(evidence_text.strip())
    item = item or {}

    if not answer.strip():
        return 0.0, ["empty_answer"]

    if not has_evidence:
        # Cannot ground claims without evidence.
        return 25.0, ["no_evidence"]

    repo = _repo(evidence)
    target = (
        (repo.get("full_name") or item.get("repo") or "")
        .split("/")[-1]
        .strip()
        .lower()
    )

    claim_checks = [
        (r"\bstars?\b", "repository.stars", repo.get("stars")),
        (r"\bforks?\b", "repository.forks", repo.get("forks")),
        (r"\blicen[cs]e\b", "repository.license", repo.get("license")),
        (r"\blanguage\b", "repository.language", repo.get("language")),
    ]
    for pattern, label, value in claim_checks:
        if re.search(pattern, lower) and not _is_present(value):
            unsupported.append(label)

    if re.search(r"\b(readme|documentation|docs)\b", lower) and not _is_present(
        evidence.get("readme")
    ):
        unsupported.append("readme")

    if re.search(r"\b(release|version|changelog)\b", lower) and not _is_present(
        evidence.get("releases")
    ):
        unsupported.append("releases")

    if re.search(r"\b(issues?|bugs?|tickets?)\b", lower) and not _is_present(
        evidence.get("issues")
    ):
        unsupported.append("issues")

    if re.search(r"\b(pull requests?|prs?\b)\b", lower) and not _is_present(
        evidence.get("pull_requests")
    ):
        unsupported.append("pull_requests")

    # Explicit numeric metric claims should match evidence values when present.
    for metric, label, value in [
        ("star", "repository.stars", repo.get("stars")),
        ("fork", "repository.forks", repo.get("forks")),
    ]:
        claims = _explicit_metric_numbers_for_target(answer, metric, target)
        if not claims:
            continue
        if not _is_present(value):
            unsupported.append(label)
            continue
        try:
            expected_int = int(value)
        except (TypeError, ValueError):
            continue
        if any(not _numbers_close(claimed, expected_int) for claimed in claims):
            unsupported.append(f"number:{label}")

    # Deduplicate
    seen: set[str] = set()
    unique: list[str] = []
    for claim in unsupported:
        if claim not in seen:
            seen.add(claim)
            unique.append(claim)

    # Positive signal: answer shares tokens with evidence (simple overlap).
    answer_tokens = set(re.findall(r"[a-z0-9]{4,}", lower))
    evidence_tokens = set(re.findall(r"[a-z0-9]{4,}", evidence_text))
    overlap = len(answer_tokens & evidence_tokens)
    overlap_bonus = min(20.0, overlap * 1.5)

    penalty = min(70.0, len(unique) * 12.0)
    score = max(0.0, min(100.0, 85.0 + overlap_bonus - penalty))
    if unique and score > 70:
        score = max(30.0, 70.0 - (len(unique) - 1) * 8.0)

    return score, unique


def _score_contradictions(
    answer: str,
    evidence: dict[str, Any],
    item: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
    """Detect obvious numeric / categorical mismatches vs evidence."""
    contradictions: list[str] = []
    lower = answer.lower()
    repo = _repo(evidence)
    item = item or {}
    target = (
        (repo.get("full_name") or item.get("repo") or "")
        .split("/")[-1]
        .strip()
        .lower()
    )

    numeric_fields = [
        ("star", "stars", repo.get("stars")),
        ("fork", "forks", repo.get("forks")),
    ]
    for metric, label, expected in numeric_fields:
        if expected is None:
            continue
        try:
            expected_int = int(expected)
        except (TypeError, ValueError):
            continue
        claimed_values = _explicit_metric_numbers_for_target(answer, metric, target)
        unique_claims = list(dict.fromkeys(claimed_values))
        for claimed in unique_claims:
            if not _numbers_close(claimed, expected_int):
                contradictions.append(
                    f"{label}: answer={claimed} evidence={expected_int}"
                )

    # License mismatch
    license_value = repo.get("license")
    if isinstance(license_value, str) and license_value.strip() and re.search(
        r"\blicen[cs]e\b", lower
    ):
        if license_value.lower() not in lower:
            # Only flag if answer asserts a different known license family.
            known = ["mit", "apache", "gpl", "bsd", "mpl", "unlicense", "agpl"]
            mentioned = [name for name in known if re.search(rf"\b{name}\b", lower)]
            evidence_lower = license_value.lower()
            if mentioned and not any(name in evidence_lower for name in mentioned):
                contradictions.append(
                    f"license: answer mentions {mentioned} evidence={license_value}"
                )

    # Language mismatch
    language = repo.get("language")
    if isinstance(language, str) and language.strip() and re.search(r"\blanguage\b", lower):
        if language.lower() not in lower:
            known_langs = [
                "python",
                "javascript",
                "typescript",
                "java",
                "go",
                "rust",
                "c++",
                "ruby",
            ]
            mentioned = [name for name in known_langs if re.search(rf"\b{re.escape(name)}\b", lower)]
            if mentioned and language.lower() not in mentioned:
                contradictions.append(
                    f"language: answer mentions {mentioned} evidence={language}"
                )

    if not contradictions:
        return 100.0, []

    score = max(0.0, 100.0 - len(contradictions) * 35.0)
    return score, contradictions


def _score_completeness(
    item: dict[str, Any],
    answer: str,
    evidence: dict[str, Any],
) -> float:
    """Check whether the answer addresses the question intent."""
    if not answer.strip():
        return 0.0

    intent = (item.get("intent") or "").strip()
    question = (item.get("question") or "").lower()
    lower = answer.lower()
    length = len(answer.strip())

    if length < 40:
        length_score = 45.0
    elif length < 120:
        length_score = 70.0
    elif length < 300:
        length_score = 85.0
    else:
        length_score = 95.0

    keywords = INTENT_KEYWORDS.get(intent, [])
    keyword_hits = sum(1 for kw in keywords if kw in lower or kw in question)
    if keywords:
        keyword_score = min(100.0, 40.0 + (keyword_hits / max(len(keywords), 1)) * 60.0)
    else:
        keyword_score = 70.0

    # Soft boost if required evidence paths are mentioned / used in answer context.
    required = item.get("required_evidence") or []
    required_hits = 0
    for path in required:
        key = path.split(".")[-1].replace("_", " ")
        if key and key.lower() in lower:
            required_hits += 1
        elif path in ("readme", "releases", "issues", "pull_requests") and path.replace(
            "_", " "
        ) in lower:
            required_hits += 1
    required_bonus = 0.0
    if required:
        required_bonus = (required_hits / len(required)) * 10.0

    # Penalize if evidence exists but answer is generic refusal / empty of substance.
    refusal = bool(
        re.search(r"\b(i don't know|cannot determine|no information|unable to)\b", lower)
    )
    refusal_penalty = 40.0 if refusal and _flatten_evidence_text(evidence).strip() else 0.0

    score = 0.55 * length_score + 0.45 * keyword_score + required_bonus - refusal_penalty
    return max(0.0, min(100.0, score))
