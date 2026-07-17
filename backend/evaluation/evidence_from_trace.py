"""Assemble a GitHubEvidence-like dict from agent tool traces (evaluation only)."""

from __future__ import annotations

from typing import Any


def evidence_from_trace(trace: list[dict[str, Any]] | None) -> dict[str, Any]:
    """
    Convert ChatService tool trace into a flat evidence dict:

    {
      "repository": {...} | None,
      "readme": str | None,
      "releases": [...],
      "issues": [...],
      "pull_requests": [...],
    }

    Does not modify EvidenceBuilder / Tools / Agent.
    """
    repository: dict[str, Any] | None = None
    readme: str | None = None
    releases: list[Any] = []
    issues: list[Any] = []
    pull_requests: list[Any] = []

    for step in trace or []:
        tool = step.get("tool")
        output = step.get("output")

        if tool == "get_repository" and isinstance(output, dict):
            repository = output

        elif tool == "get_readme":
            readme = _normalize_readme(output)

        elif tool == "get_releases":
            releases = _normalize_list(output, "recent_releases")

        elif tool == "get_issues":
            issues = _normalize_list(output, "recent_issues")

        elif tool == "get_pull_requests":
            pull_requests = _normalize_list(output, "recent_pull_requests")

    return {
        "repository": repository,
        "readme": readme,
        "releases": releases,
        "issues": issues,
        "pull_requests": pull_requests,
    }


def _normalize_readme(output: Any) -> str | None:
    if output is None:
        return None
    if isinstance(output, str):
        return output or None
    if isinstance(output, dict):
        preview = output.get("preview")
        length = output.get("length") or 0
        if isinstance(preview, str) and preview.strip():
            return preview
        if length:
            return f"[readme length={length}]"
    return None


def _normalize_list(output: Any, key: str) -> list[Any]:
    if output is None:
        return []
    if isinstance(output, list):
        return output
    if isinstance(output, dict):
        value = output.get(key, [])
        return value if isinstance(value, list) else []
    return []
