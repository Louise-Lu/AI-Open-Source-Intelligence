# 共享基础设施：客户端、环境辅助、装饰器、记录逻辑

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import requests
import yaml

from agent.tool_gateway import tool_gateway, with_tool_gateway
from agent.schemas.discovery_result import discovery_result
from sources.github.client import GitHubAPI
from sources.huggingface.client import HuggingFaceClient

# 全局客户端实例
github = GitHubAPI()
huggingface = HuggingFaceClient()

# Agent Reach 的 CLI 工具装在 ~/.agent-reach-venv/bin/
# opencli 装在 nvm 管理的 node 下，需要额外加到 PATH
_AGENT_REACH_BIN = str(Path.home() / ".agent-reach-venv" / "bin")
_NVM_NODE_BIN = str(Path.home() / ".nvm" / "versions" / "node" / "v20.19.0" / "bin")
_PODCAST_SCRIPT = str(Path.home() / ".agent-reach" / "tools" / "xiaoyuzhou" / "transcribe.sh")


# ── Agent Reach 环境辅助 ──

def agent_reach_env() -> dict[str, str]:
    """构建干净的子进程环境，避免 TRAE 的 Python 路径污染 Agent Reach 工具。"""
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    # opencli 装在 nvm 的 node 下，必须加入 PATH 否则 subprocess 找不到
    extra_bins = [_AGENT_REACH_BIN]
    if Path(_NVM_NODE_BIN).exists():
        extra_bins.insert(0, _NVM_NODE_BIN)
    env["PATH"] = os.pathsep.join(extra_bins) + os.pathsep + env.get("PATH", "")
    return env


def load_agent_reach_config() -> dict[str, Any]:
    """读取 Agent Reach 配置。注意：不要打印 token/cookie。"""
    path = Path.home() / ".agent-reach" / "config.yaml"
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def run_agent_reach_cmd(cmd: list[str], *, timeout: int = 30, env: dict[str, str] | None = None) -> tuple[bool, str, str]:
    """运行 Agent Reach 相关命令，返回 ok/stdout/stderr。"""
    envc = agent_reach_env()
    if env:
        envc.update(env)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=envc,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except FileNotFoundError:
        return False, "", f"tool-not-found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as exc:
        return False, "", str(exc)


# ── 通用辅助函数 ──

def truncate_text(text: Any, limit: int = 4000) -> str:
    """截断工具输出，避免 observation 过长。"""
    if text is None:
        return ""
    value = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    return value if len(value) <= limit else value[:limit] + "...(truncated)"


def parse_vtt(content: str) -> str:
    """简单解析 VTT 字幕文件，提取纯文本。"""
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or "-->" in line:
            continue
        if line.isdigit():
            continue
        lines.append(line)
    return "\n".join(lines)


# ── Policy / Trace 装饰器 ──

def print_policy_hint(label: str, tool_name: str) -> None:
    """进入 tool 前 / 调用 tool 后，打印当前的 policy_state。"""
    tool_gateway.print_policy_hint(label, tool_name)


def with_policy_logging(tool_name: str):
    """给所有 tool 加 decorator，进入 tool 前会先检查 Runtime Policy。"""
    return with_tool_gateway(tool_name)


# ── 记录与结果格式化 ──

def record(
    tool_name: str,
    tool_input: dict,
    tool_output,
    *,
    update_policy: bool = True,
    blocked: bool = False,
):
    """tool 调用之后：更新 policy_state、更新 trace、返回带动态进度的 observation。"""
    return tool_gateway.record(
        tool_name,
        tool_input,
        tool_output,
        update_policy=update_policy,
        blocked=blocked,
    )


def capability_result(
    *,
    source: str,
    evidence_type: str,
    summary: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """统一 Capability Tool 返回结构。"""
    return {
        "source": source,
        "type": evidence_type,
        "summary": summary,
        "evidence": evidence,
    }
