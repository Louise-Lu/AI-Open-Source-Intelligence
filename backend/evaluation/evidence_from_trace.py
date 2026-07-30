"""Assemble evidence dict from agent tool traces (evaluation only).

Supports the ACTUAL trace format produced by agent/trace.py:
  {"tool": str, "input": dict, "output": Any}

Also handles ToolGateway-wrapped output:
  {"result": Any, "policy_hint": dict}

And Capability Tool output structure:
  {"source": str, "type": str, "summary": str, "evidence": dict}
"""

from __future__ import annotations

from typing import Any


def _unwrap_output(output: Any) -> Any:
    """Unwrap ToolGateway wrapper: {"result": ..., "policy_hint": ...} → inner result."""
    if isinstance(output, dict) and "result" in output and "policy_hint" in output:
        return output["result"]
    return output


def evidence_from_trace(trace: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, Any]:
    """
    Convert agent tool trace into a flat evidence dict:

    {
      "repository": {...} | None,
      "readme": str | None,
      "releases": [...],
      "issues": [...],
      "pull_requests": [...],
      "community_posts": [...],
      "web_pages": [...],
    }

    Does not modify EvidenceBuilder / Tools / Agent.
    """
    repository: dict[str, Any] | None = None
    readme: str | None = None
    releases: list[Any] = []
    issues: list[Any] = []
    pull_requests: list[Any] = []
    community_posts: list[Any] = []
    web_pages: list[Any] = []

    # Normalize trace to list of steps
    steps = _extract_steps(trace)

    for step in steps:
        if not isinstance(step, dict):
            continue

        # ── Extract tool name ──
        # Primary format (agent/trace.py): {"tool": str, "input": dict, "output": Any}
        tool = step.get("tool")
        raw_output = step.get("output")

        # Legacy format fallback: {"action": {"tool": ...}, "observation": ...}
        if not tool:
            action = step.get("action")
            if isinstance(action, dict):
                tool = action.get("tool")
                raw_output = step.get("raw_output")
                if raw_output is None:
                    raw_output = step.get("observation")

        if not tool:
            continue

        # Unwrap ToolGateway wrapper
        output = _unwrap_output(raw_output)

        # ── Discovery tools ──
        if tool == "github_search":
            # Discovery only, no direct evidence
            pass

        elif tool == "web_search" and isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("url") or item.get("identifier"):
                    web_pages.append(item)

        elif tool == "community_search" and isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("identifier"):
                    community_posts.append(item)

        # ── Capability tools (new format) ──
        # These return: {"source": str, "type": str, "summary": str, "evidence": dict}
        elif tool == "github_project_profile" and isinstance(output, dict):
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                repo = evidence.get("repository")
                if isinstance(repo, dict) and repo:
                    repository = repo
                rm = evidence.get("readme")
                if rm:
                    readme = _normalize_readme(rm)

        elif tool == "github_project_health" and isinstance(output, dict):
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                iss = evidence.get("issues")
                if isinstance(iss, list):
                    issues = iss
                prs = evidence.get("pull_requests")
                if isinstance(prs, list):
                    pull_requests = prs

        elif tool == "github_release_summary" and isinstance(output, dict):
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                rel = evidence.get("releases")
                if isinstance(rel, list):
                    releases = rel

        elif tool == "webpage_reader" and isinstance(output, dict):
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                web_pages.append({
                    "url": evidence.get("url"),
                    "content": evidence.get("content"),
                })
            elif output.get("source") == "web":
                # Web capability tool format
                web_pages.append({
                    "url": output.get("summary", ""),
                    "content": str(output.get("evidence", "")),
                })

        elif tool == "community_reader" and isinstance(output, dict):
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                community_posts.append({
                    "identifier": evidence.get("identifier"),
                    "platform": evidence.get("platform"),
                    "content": evidence.get("content"),
                })
            elif output.get("source") == "community":
                community_posts.append({
                    "identifier": output.get("summary", ""),
                    "platform": "community",
                    "content": str(output.get("evidence", "")),
                })

        elif tool == "huggingface_model_profile" and isinstance(output, dict):
            # HF evidence goes to web_pages as supplementary
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                web_pages.append({
                    "url": f"huggingface://{evidence.get('model', {}).get('id', '')}",
                    "content": str(evidence),
                })

        # ── Legacy tool names (backward compatibility) ──
        elif tool in {"get_repository", "get_repository_info"} and isinstance(output, dict):
            repository = output

        elif tool in {"get_readme", "readme"}:
            readme = _normalize_readme(output)

        elif tool in {"get_releases", "releases"}:
            releases = _normalize_list(output, "recent_releases")

        elif tool in {"get_issues", "issues"}:
            issues = _normalize_list(output, "recent_issues")

        elif tool in {"get_pull_requests", "pull_requests"}:
            pull_requests = _normalize_list(output, "recent_pull_requests")

    return {
        "repository": repository,
        "readme": readme,
        "releases": releases,
        "issues": issues,
        "pull_requests": pull_requests,
        "community_posts": community_posts,
        "web_pages": web_pages,
    }


def _extract_steps(trace: Any) -> list[dict[str, Any]]:
    """Normalize trace to a flat list of step dicts."""
    if isinstance(trace, dict):
        # Try multiple keys for the step list
        for key in ("steps", "tool_trace", "tool_calls"):
            val = trace.get(key)
            if isinstance(val, list):
                return val
        return []
    elif isinstance(trace, list):
        return trace
    return []


def _normalize_readme(output: Any) -> str | None:
    if output is None:
        return None
    if isinstance(output, str):
        return output or None
    if isinstance(output, dict):
        preview = output.get("preview")
        content = output.get("content")
        length = output.get("length") or 0
        if isinstance(content, str) and content.strip():
            return content
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
