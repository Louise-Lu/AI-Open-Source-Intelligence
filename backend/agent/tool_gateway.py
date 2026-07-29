from __future__ import annotations

import time
from functools import wraps
from inspect import signature
from typing import Any, Callable

from agent.research_policy import after_tool_call, before_tool_call, build_policy_hint
from agent.trace import add_trace


class ToolGateway:
    """统一工具调用入口：Policy 拦截、异常归一化、Policy/Trace 记录。"""

    def before(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any] | None:
        self.print_policy_hint("BEFORE", tool_name)
        return before_tool_call(tool_name, tool_input)

    def record(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        *,
        update_policy: bool = True,
        blocked: bool = False,
    ) -> dict[str, Any]:
        if update_policy:
            after_tool_call(tool_name, tool_output)

        add_trace(tool_name, tool_input, tool_output)
        self.print_policy_hint("BLOCKED" if blocked else "AFTER", tool_name)

        return {
            "result": tool_output,
            "policy_hint": build_policy_hint(),
        }

    def error(self, tool_name: str, tool_input: dict[str, Any], exc: Exception) -> dict[str, Any]:
        tool_output = {
            "source": "tool_gateway",
            "type": "tool_error",
            "summary": f"{tool_name} 调用失败。",
            "evidence": {
                "tool": tool_name,
                "input": tool_input,
                "error_type": exc.__class__.__name__,
                "error": str(exc),
            },
        }
        return self.record(tool_name, tool_input, tool_output)

    @staticmethod
    def print_policy_hint(label: str, tool_name: str) -> None:
        print(f"\n========== POLICY {label}: {tool_name} ==========")
        print(build_policy_hint())


tool_gateway = ToolGateway()


def tool_input_from_call(func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    """从工具函数调用参数中还原 tool_input，用于 Runtime Policy 和 trace。"""
    try:
        bound = signature(func).bind_partial(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except Exception:
        return dict(kwargs)


def with_tool_gateway(tool_name: str):
    """给 LangChain tool 包一层统一网关。"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tool_input = tool_input_from_call(func, args, kwargs)
            started_at = time.perf_counter()
            blocked = tool_gateway.before(tool_name, tool_input)
            if blocked:
                print(f"[ToolGateway] {tool_name} blocked in {time.perf_counter() - started_at:.2f}s")
                return tool_gateway.record(
                    tool_name,
                    tool_input,
                    blocked,
                    update_policy=False,
                    blocked=True,
                )
            try:
                result = func(*args, **kwargs)
                print(f"[ToolGateway] {tool_name} finished in {time.perf_counter() - started_at:.2f}s")
                return result
            except Exception as exc:
                print(f"[ToolGateway] {tool_name} failed in {time.perf_counter() - started_at:.2f}s")
                return tool_gateway.error(tool_name, tool_input, exc)

        return wrapper

    return decorator
