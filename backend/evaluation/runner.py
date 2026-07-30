"""
Evaluation Runner — AI Intelligence Research Agent.

新架构:
  User Query
  → IntentRouter → EntityResolver → ExecutionPlanBuilder → ExecutionPlan
  → ResearchPolicy Runtime → ReAct Agent → Tools → Evidence
  → Research Findings

评测维度:
  1. Intent Accuracy
  2. ExecutionPlan
  3. Tool Efficiency
  4. Evidence Quality
  5. Research Completeness (LLM Judge)
  6. Runtime Performance

Usage (from backend/):

    python -m evaluation.runner
    python -m evaluation.runner --limit 5
    python -m evaluation.runner --ids 1,2,3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# 当作为脚本运行时，确保`backend/`位于sys.path上.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.evaluators import (  # noqa: E402
    evaluate_intent,
    evaluate_context_builder,
    evaluate_tool_efficiency,
    evaluate_evidence_quality_v2,
    evaluate_research_completeness,
    evaluate_answer_quality,
    evaluate_runtime_performance,
)
from evaluation.evidence_from_trace import evidence_from_trace  # noqa: E402
from evaluation.report import write_report  # noqa: E402

from research_agent.intent import IntentRouter  # noqa: E402
from research_agent.entity_extractor import EntityExtractor  # noqa: E402
from research_agent.entity_resolver import EntityResolver  # noqa: E402
from research_agent.context_builder import ExecutionPlanBuilder  # noqa: E402
from research_agent.services.chat_service import ChatService  # noqa: E402

from agent.intelligence_agent import build_intelligence_agent_prompt, intelligence_agent  # noqa: E402
from agent.research_policy import (  # noqa: E402
    clear_research_policy,
    start_research_policy,
    sync_research_policy_from_trace,
)
from agent.trace import (  # noqa: E402
    clear_trace,
    get_trace,
    populate_trace_from_agent_result,
)


EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "dataset" / "research_cases.json"


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON list of research case objects.")
    return data


def run_case(
    service: ChatService,
    intent_router: IntentRouter,
    entity_extractor: EntityExtractor,
    entity_resolver: EntityResolver,
    plan_builder: ExecutionPlanBuilder,
    case: dict[str, Any],
) -> dict[str, Any]:
    """执行单个评测用例，返回完整 trace + 评估结果。

    流程:
    1. IntentRouter → intent
    2. EntityExtractor + EntityResolver → entities
    3. ExecutionPlanBuilder → execution_plan
    4. Agent invoke → agent_result
    5. 从 agent_result 提取 trace / evidence / answer
    6. 运行 6 个 evaluator
    """
    query = case.get("query") or ""
    case_id = case.get("id")
    category = case.get("category", "unknown")

    print(f"  [{case_id}] 开始: {query[:60]}...")

    # ── Phase 1: Intent ──
    t_intent = time.perf_counter()
    predicted_intent_dict: dict[str, Any] = {}
    intent_error = None
    try:
        intent = intent_router.route(query)
        predicted_intent_dict = {
            "objective": intent.objective,
            "focus": intent.focus or [],
            "depth": intent.depth,
            "entities": intent.entities or [],
        }
    except Exception as exc:
        intent_error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    intent_latency = time.perf_counter() - t_intent

    # ── Phase 2: Entity Resolution ──
    t_entity = time.perf_counter()
    resolved_entities: list[Any] = []
    try:
        # 使用 intent 中的 entities
        entity_names = set(predicted_intent_dict.get("entities") or [])
        if not entity_names:
            entity_result = entity_extractor.extract(query)
            entity_dict = (
                entity_result
                if isinstance(entity_result, dict)
                else entity_result.model_dump()
            )
            for entity in entity_dict.get("entities", []):
                name = entity.get("name", "")
                if name:
                    entity_names.add(name)

        for name in entity_names:
            if name:
                result = entity_resolver.resolve(name)
                if result and result.name:
                    resolved_entities.append(result)
    except Exception as exc:
        print(f"  [{case_id}] 实体解析失败: {exc}")
    entity_latency = time.perf_counter() - t_entity

    # ── Phase 3: ExecutionPlan ──
    t_plan = time.perf_counter()
    execution_plan_dict: dict[str, Any] = {}
    plan = None
    try:
        plan = plan_builder.build(intent, resolved_entities)
        if plan is not None:
            execution_plan_dict = plan.model_dump()
    except Exception as exc:
        print(f"  [{case_id}] ExecutionPlan 构建失败: {exc}")
    plan_latency = time.perf_counter() - t_plan

    # ── Phase 4: Agent ──
    t_agent = time.perf_counter()
    agent_error = None
    agent_result: dict[str, Any] = {"messages": []}
    answer = ""
    try:
        if plan is not None:
            clear_trace()
            start_research_policy(plan)
            agent_prompt = build_intelligence_agent_prompt(plan, resolved_entities)

            # 计算 recursion_limit
            max_tool_calls = int(getattr(plan, "max_tool_calls", 8) or 8)
            recursion_limit = max(12, max_tool_calls * 2 + 6)

            agent_result = intelligence_agent.invoke(
                {
                    "messages": [
                        ("system", agent_prompt),
                        ("user", query),
                    ]
                },
                config={"recursion_limit": recursion_limit},
            )
        else:
            # 没有 plan，直接用 ChatService
            result = service.chat(query)
            answer = result.get("answer") or ""
            agent_result = result
    except Exception as exc:
        agent_error = f"{type(exc).__name__}: {exc}"
        print(f"  [{case_id}] Agent 调用失败: {agent_error}")
        traceback.print_exc()
    agent_latency = time.perf_counter() - t_agent

    # ── Phase 5: 从 agent_result 提取 trace / evidence / answer ──
    t_final = time.perf_counter()

    if plan is not None:
        populate_trace_from_agent_result(agent_result)
        sync_research_policy_from_trace(get_trace())

    trace = get_trace()
    trace_dict: dict[str, Any] = {}
    if isinstance(trace, dict):
        trace_dict = trace
    elif isinstance(trace, list):
        trace_dict = {"steps": trace}
    else:
        trace_dict = {"steps": []}

    # 提取 evidence
    evidence = evidence_from_trace(trace)

    # 提取 answer
    if not answer:
        answer = _extract_final_answer(agent_result)

    final_latency = time.perf_counter() - t_final

    total_latency = intent_latency + entity_latency + plan_latency + agent_latency + final_latency

    # 清理 policy
    try:
        clear_research_policy()
    except Exception:
        pass

    # ── Phase 6: 运行 6 个 evaluator ──
    print(f"  [{case_id}] 评估中...")

    intent_eval = evaluate_intent(case, predicted_intent_dict)
    context_eval = evaluate_context_builder(case, execution_plan_dict)
    tool_eval = evaluate_tool_efficiency(case, trace_dict)
    evidence_eval = evaluate_evidence_quality_v2(case, evidence, answer)
    completeness_eval = evaluate_research_completeness(case, answer, evidence)
    answer_eval = evaluate_answer_quality(case, answer)
    performance_eval = evaluate_runtime_performance(
        case,
        total_latency,
        trace_dict,
        answer,
        phase_timings={
            "intent": round(intent_latency, 3),
            "context_builder": round(plan_latency, 3),
            "agent": round(agent_latency, 3),
            "final_generation": round(final_latency, 3),
        },
    )

    # ── 构建完整结果 ──
    record: dict[str, Any] = {
        "id": case_id,
        "query": query,
        "category": category,
        "error": agent_error or intent_error,
        "latency_seconds": round(total_latency, 3),
        # 完整 trace
        "full_trace": {
            "intent": predicted_intent_dict,
            "execution_plan": execution_plan_dict,
            "tool_trace": trace_dict.get("steps") or [],
            "evidence": evidence,
            "final_answer": answer,
        },
        # 评估结果
        "evaluations": {
            "intent_accuracy": intent_eval,
            "context_builder": context_eval,
            "tool_efficiency": tool_eval,
            "evidence_quality": evidence_eval,
            "research_completeness": completeness_eval,
            "answer_quality": answer_eval,
            "runtime_performance": performance_eval,
        },
    }

    # 打印单行摘要
    status = "错误" if record["error"] else "成功"
    print(
        f"  [{case_id}] {status}  "
        f"意图={intent_eval['score']}  "
        f"计划={context_eval['score']}  "
        f"效率={tool_eval['score']}  "
        f"证据={evidence_eval['score']}  "
        f"完整={completeness_eval['score']}  "
        f"回答={answer_eval['score']}  "
        f"延迟={total_latency:.1f}s"
    )

    return record


def _extract_final_answer(agent_result: Any) -> str:
    """从 agent result 中提取最终回答。"""
    if isinstance(agent_result, dict):
        # ChatService 返回格式
        answer = agent_result.get("answer")
        if answer:
            return answer

        # LangGraph 返回格式: 从 messages 中提取最后的 AI 消息
        messages = agent_result.get("messages") or []
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                # 跳过 tool messages
                if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                    continue
                if hasattr(msg, "type") and msg.type == "tool":
                    continue
                return msg.content
            elif isinstance(msg, dict):
                content = msg.get("content", "")
                if content and msg.get("role") != "tool":
                    return content

    if isinstance(agent_result, str):
        return agent_result

    return ""


def run(
    limit: int | None = None,
    ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """运行评测。"""
    dataset = load_dataset()

    if ids:
        id_set = set(ids)
        dataset = [item for item in dataset if item.get("id") in id_set]

    if limit is not None:
        dataset = dataset[:limit]

    # 初始化组件
    service = ChatService()
    intent_router = IntentRouter()
    entity_extractor = EntityExtractor()
    entity_resolver = EntityResolver()
    plan_builder = ExecutionPlanBuilder()

    results: list[dict[str, Any]] = []

    print(f"=" * 60)
    print(f"AI Intelligence Agent 评测")
    print(f"测试用例数量: {len(dataset)}")
    print(f"=" * 60)

    for index, case in enumerate(dataset, start=1):
        case_id = case.get("id")
        category = case.get("category", "unknown")
        print(f"\n[{index}/{len(dataset)}] id={case_id} category={category}")

        try:
            record = run_case(
                service, intent_router, entity_extractor,
                entity_resolver, plan_builder, case,
            )
            results.append(record)

        except Exception as exc:
            print(f"  [{case_id}] 评测失败: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            results.append({
                "id": case_id,
                "query": case.get("query", ""),
                "category": category,
                "error": f"{type(exc).__name__}: {exc}",
                "latency_seconds": 0,
                "full_trace": {},
                "evaluations": {},
            })

    # 生成报告
    summary = write_report(results)

    print(f"\n{'=' * 60}")
    print("=== 评测摘要 ===")
    print(f"{'=' * 60}")
    print(f"综合分:         {summary.get('overall_display', '-')}")
    print(f"意图理解:       {summary.get('intent_accuracy_display', '-')}")
    print(f"计划质量:       {summary.get('context_plan_display', '-')}")
    print(f"平均工具调用:   {summary.get('avg_tool_calls_display', '-')}")
    print(f"工具效率:       {summary.get('tool_efficiency_display', '-')}")
    print(f"来源覆盖 Recall:{summary.get('source_recall_display', '-')}")
    print(f"证据质量:       {summary.get('evidence_quality_display', '-')}")
    print(f"研究完整性:     {summary.get('completeness_display', '-')}")
    print(f"回答质量:       {summary.get('answer_quality_display', '-')}")
    print(f"平均延迟:       {summary.get('avg_latency_display', '-')}")
    print(f"估算成本:       {summary.get('total_cost_display', '-')}")
    print(f"\n报告: {summary.get('report_path')}")
    print(f"结果: {summary.get('results_path')}")

    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Intelligence Agent 评测 Runner")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只运行前 N 个用例。",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="逗号分隔的用例 id，例如 1,2,5",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    ids = None
    if args.ids:
        ids = [int(part.strip()) for part in args.ids.split(",") if part.strip()]
    run(limit=args.limit, ids=ids)


if __name__ == "__main__":
    main()
