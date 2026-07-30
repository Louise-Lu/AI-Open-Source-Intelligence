"""Evidence Quality Evaluator v2.

检查每个 final conclusion 是否有 evidence 支撑。

评分规则:
  0: 没有证据
  1: 有相关来源
  2: 来源直接支持结论

输出: evidence_quality_score (0-100)
"""

from __future__ import annotations

import re
from typing import Any


def _flatten_evidence_text(evidence: dict[str, Any]) -> str:
    """将 evidence dict 展平为文本。"""
    chunks: list[str] = []

    def walk(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        else:
            chunks.append(str(value))

    walk(evidence)
    return " ".join(chunks).lower()


def _count_evidence_sources(evidence: dict[str, Any]) -> dict[str, int]:
    """统计各来源的证据数量。"""
    counts: dict[str, int] = {}

    if evidence.get("repository"):
        counts["github"] = counts.get("github", 0) + 1
    if evidence.get("readme"):
        counts["github"] = counts.get("github", 0) + 1
    if evidence.get("releases"):
        counts["github"] = counts.get("github", 0) + len(evidence.get("releases", []))
    if evidence.get("issues"):
        counts["github"] = counts.get("github", 0) + len(evidence.get("issues", []))
    if evidence.get("pull_requests"):
        counts["github"] = counts.get("github", 0) + len(evidence.get("pull_requests", []))
    if evidence.get("community_posts"):
        counts["community"] = counts.get("community", 0) + len(evidence.get("community_posts", []))
    if evidence.get("web_pages"):
        counts["web"] = counts.get("web", 0) + len(evidence.get("web_pages", []))

    return counts


def _check_claims_grounded(answer: str, evidence: dict[str, Any]) -> tuple[int, int, list[str]]:
    """检查回答中的声明是否有证据支撑。

    Returns:
        (total_claims, grounded_claims, unsupported_list)
    """
    if not answer or not answer.strip():
        return 0, 0, ["empty_answer"]

    evidence_text = _flatten_evidence_text(evidence)
    if not evidence_text.strip():
        # 有回答但没有证据
        return 1, 0, ["no_evidence_for_answer"]

    total_claims = 0
    grounded_claims = 0
    unsupported: list[str] = []

    lower = answer.lower()

    # 检查数值声明
    numbers = re.findall(r"\b(\d{2,})\b", answer.replace(",", ""))
    for number in numbers[:10]:
        total_claims += 1
        if number in evidence_text.replace(",", ""):
            grounded_claims += 1
        else:
            # 年份不算需要证据的数值
            if number.startswith("20") and len(number) == 4:
                total_claims -= 1
                continue
            unsupported.append(f"number:{number}")

    # 检查关键属性声明
    repo = evidence.get("repository") if isinstance(evidence.get("repository"), dict) else {}
    attr_checks = [
        (r"\bstar", "stars", repo.get("stars")),
        (r"\bfork", "forks", repo.get("forks")),
        (r"\blicen[cs]e", "license", repo.get("license")),
        (r"\blanguage", "language", repo.get("language")),
    ]
    for pattern, label, value in attr_checks:
        if re.search(pattern, lower):
            total_claims += 1
            if value is not None and str(value).lower() in evidence_text:
                grounded_claims += 1
            elif value is not None:
                grounded_claims += 1  # 有值但未在文本中精确匹配，给半分
            else:
                unsupported.append(f"attr:{label}")

    # 检查来源引用
    source_checks = [
        (r"\b(readme|documentation|docs)\b", "readme", evidence.get("readme")),
        (r"\b(release|version|changelog)\b", "releases", evidence.get("releases")),
        (r"\b(issue|bug|ticket)\b", "issues", evidence.get("issues")),
        (r"\b(reddit|community|forum|discussion)\b", "community", evidence.get("community_posts")),
    ]
    for pattern, label, value in source_checks:
        if re.search(pattern, lower):
            total_claims += 1
            if value is not None and (isinstance(value, (str, list)) and len(value) > 0
                                      or isinstance(value, dict) and value):
                grounded_claims += 1
            else:
                unsupported.append(f"source:{label}")

    # 去重
    seen: set[str] = set()
    unique_unsupported: list[str] = []
    for claim in unsupported:
        if claim not in seen:
            seen.add(claim)
            unique_unsupported.append(claim)

    if total_claims == 0:
        # 没有可验证的声明，给基础分
        return 1, 1, []

    return total_claims, grounded_claims, unique_unsupported


def evaluate_evidence_quality_v2(
    case: dict[str, Any],
    evidence: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    """评估证据质量。

    Args:
        case: 评测用例
        evidence: 从 trace 提取的证据 dict
        answer: Agent 最终回答

    Returns:
        评估结果 dict
    """
    evidence = evidence or {}
    answer = answer or ""

    # 1. 统计来源
    source_counts = _count_evidence_sources(evidence)
    total_sources = sum(source_counts.values())
    unique_sources = len(source_counts)

    # 2. 检查声明是否有证据支撑
    total_claims, grounded_claims, unsupported = _check_claims_grounded(answer, evidence)

    # 3. 计算评分
    # 基础分：有证据 = 1，无证据 = 0
    if total_sources == 0:
        base_score = 0
    elif total_sources <= 2:
        base_score = 1
    else:
        base_score = 2

    # 支撑率
    grounding_ratio = grounded_claims / total_claims if total_claims > 0 else 0.0

    # 最终分数 (0-100)
    # base_score: 0/1/2 → 映射到 0/50/100
    base_points = base_score * 50.0
    # grounding 加权 50%
    grounding_points = grounding_ratio * 50.0
    # 多来源加分
    source_bonus = min(10.0, unique_sources * 3.0)

    final_score = min(100.0, base_points + grounding_points + source_bonus)

    # 检查 expected_plan 中的 required_evidence 是否满足
    expected_plan = case.get("expected_plan") or {}
    required_evidence = set(expected_plan.get("required_evidence") or [])
    covered_required = required_evidence & set(source_counts.keys())
    missing_required = required_evidence - set(source_counts.keys())

    return {
        "layer": "evidence_quality",
        "implemented": True,
        "score": round(final_score),
        "details": {
            "base_level": base_score,  # 0/1/2
            "grounding_ratio": round(grounding_ratio, 3),
            "total_claims": total_claims,
            "grounded_claims": grounded_claims,
            "unsupported_claims": unsupported,
            "source_counts": source_counts,
            "unique_sources": unique_sources,
            "total_evidence_items": total_sources,
            "required_evidence": sorted(required_evidence),
            "covered_required": sorted(covered_required),
            "missing_required": sorted(missing_required),
        },
    }
