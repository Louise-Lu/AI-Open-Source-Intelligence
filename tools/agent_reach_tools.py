# Agent Reach 工具封装（简单版）
# 先跑通，后续再整合进 backend/agent/tools.py

import os
import subprocess
import json
from pathlib import Path

import yaml
import requests
from langchain.tools import tool


# ============ 辅助函数 ============

# Agent Reach 的 CLI 工具装在 ~/.agent-reach-venv/bin/
_VENV_BIN = str(Path.home() / ".agent-reach-venv" / "bin")

# 小宇宙转录脚本
_PODCAST_SCRIPT = str(Path.home() / ".agent-reach" / "tools" / "xiaoyuzhou" / "transcribe.sh")


def _build_env():
    """构建干净的子进程环境：清掉 TRAE 的 PYTHONHOME/PYTHONPATH，加上 venv bin。"""
    env = os.environ.copy()
    # TRAE 注入的 PYTHONHOME/PYTHONPATH 会干扰 venv 里的 Python 工具
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    # 把 venv bin 放到 PATH 最前面
    env["PATH"] = _VENV_BIN + os.pathsep + env.get("PATH", "")
    return env


def _load_config():
    """读取 ~/.agent-reach/config.yaml"""
    p = Path.home() / ".agent-reach" / "config.yaml"
    if p.exists():
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {}


def _truncate(text, limit=4000):
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit] + "...(truncated)"


def _run_cmd(cmd, timeout=30):
    """运行命令，返回 (ok, stdout, stderr)。"""
    env = _build_env()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        return r.returncode == 0, r.stdout, r.stderr
    except FileNotFoundError:
        return False, "", f"tool-not-found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:
        return False, "", str(e)


# ============ Twitter/X ============

@tool
def search_twitter(query: str) -> str:
    """
    搜索 Twitter/X 上的推文。
    使用这个工具当用户想了解推特上对某个话题的讨论。

    Args:
        query: 搜索关键词，比如 "AI agent"

    Returns:
        推文列表的 JSON 字符串
    """
    env = _build_env()
    cfg = _load_config()

    if cfg.get("twitter_auth_token"):
        env["TWITTER_AUTH_TOKEN"] = cfg["twitter_auth_token"]
    if cfg.get("twitter_ct0"):
        env["TWITTER_CT0"] = cfg["twitter_ct0"]

    result = subprocess.run(
        ["twitter", "search", query, "-n", "10", "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    if result.returncode == 0:
        return _truncate(result.stdout)
    # twitter CLI 的 WARNING 输出到 stderr 但不影响结果，stdout 有内容就返回
    if result.stdout.strip():
        return _truncate(result.stdout)
    return f"搜索失败: {result.stderr}"


# ============ 网页阅读 ============

@tool
def read_webpage(url: str) -> str:
    """
    读取任何网页的内容。
    使用这个工具当用户想了解某个网页的详细内容。

    Args:
        url: 网页 URL

    Returns:
        网页的纯文本内容
    """
    try:
        response = requests.get(
            f"https://r.jina.ai/{url}",
            timeout=30,
        )
        return _truncate(response.text, 8000)
    except Exception as e:
        return f"读取失败: {str(e)}"


# ============ YouTube ============

@tool
def get_youtube_transcript(url: str) -> str:
    """
    获取 YouTube 视频的字幕/转录。
    使用这个工具当用户想了解某个 YouTube 视频的内容。

    Args:
        url: YouTube 视频 URL

    Returns:
        视频字幕或转录文本
    """
    ok, stdout, stderr = _run_cmd(
        ["yt-dlp", "--write-sub", "--write-auto-sub", "--sub-lang", "zh-Hans,zh,en", "--skip-download", "-o", "/tmp/%(id)s", url],
        timeout=60,
    )
    if not ok:
        # 没有字幕，退回到元信息
        ok2, stdout2, stderr2 = _run_cmd(["yt-dlp", "--dump-json", url], timeout=60)
        if not ok2:
            return f"获取失败: {stderr2}"
        data = json.loads(stdout2)
        out = {
            "title": data.get("title"),
            "uploader": data.get("uploader"),
            "duration": data.get("duration"),
            "description": _truncate(data.get("description", ""), 2000),
            "subtitles": "无字幕",
        }
        return json.dumps(out, ensure_ascii=False)

    # 找到下载的 vtt 文件，提取文本
    video_id = url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1]
    vtt_files = list(Path("/tmp").glob(f"{video_id}*.vtt"))
    if vtt_files:
        text = _parse_vtt(vtt_files[0].read_text(encoding="utf-8"))
        return _truncate(text, 8000)
    return "字幕下载成功但未找到文件"


def _parse_vtt(content: str) -> str:
    """简单解析 VTT 字幕文件，提取纯文本。"""
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        # 跳过时间轴、序号、空行、VTT 头
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or "-->" in line:
            continue
        if line.isdigit():
            continue
        lines.append(line)
    return "\n".join(lines)


# ============ B站 ============

@tool
def search_bilibili(query: str) -> str:
    """
    搜索 B站视频。
    使用这个工具当用户想了解 B站上对某个话题的视频。

    Args:
        query: 搜索关键词

    Returns:
        搜索结果列表
    """
    ok, stdout, stderr = _run_cmd(["bili", "search", query, "--type", "video", "-n", "5"], timeout=30)
    if ok:
        return _truncate(stdout)
    # bili-cli 不可用时，用搜索 API 直连
    try:
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        # 先拿 cookie
        requests.get("https://www.bilibili.com/", headers={"User-Agent": ua}, timeout=10)
        resp = requests.get(
            "https://api.bilibili.com/x/web-interface/search/all/v2",
            params={"keyword": query, "page": 1},
            headers={"User-Agent": ua, "Referer": "https://www.bilibili.com/"},
            timeout=10,
        )
        data = resp.json()
        results = []
        for item in data.get("data", {}).get("result", []):
            if item.get("result_type") == "video":
                for v in item.get("data", [])[:5]:
                    results.append({
                        "title": v.get("title", "").replace('<em class="keyword">', "").replace("</em>", ""),
                        "bvid": v.get("bvid"),
                        "play": v.get("play"),
                        "up": v.get("author"),
                    })
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return f"搜索失败: {e}"


# ============ V2EX ============

@tool
def search_v2ex(query: str) -> str:
    """
    获取 V2EX 上的热门主题。
    使用这个工具当用户想了解 V2EX 社区最近在讨论什么。

    Args:
        query: 搜索关键词（V2EX 搜索 API 已废弃，改用热门主题）

    Returns:
        主题列表的 JSON 字符串
    """
    try:
        resp = requests.get(
            "https://www.v2ex.com/api/topics/hot.json",
            headers={"User-Agent": "agent-reach/1.0"},
            timeout=10,
        )
        data = resp.json()
        # V2EX 没有 search API 了，返回热门主题，按 query 过滤标题
        results = [
            {
                "title": t.get("title"),
                "url": t.get("url"),
                "replies": t.get("replies"),
                "node": t.get("node", {}).get("title"),
                "member": t.get("member", {}).get("username"),
            }
            for t in (data or [])
            if query.lower() in t.get("title", "").lower()
        ][:10]
        # 如果没匹配到，返回前10条热门
        if not results:
            results = [
                {
                    "title": t.get("title"),
                    "url": t.get("url"),
                    "replies": t.get("replies"),
                    "node": t.get("node", {}).get("title"),
                    "member": t.get("member", {}).get("username"),
                }
                for t in (data or [])[:10]
            ]
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return f"获取失败: {e}"


# ============ RSS ============

@tool
def read_rss(url: str) -> str:
    """
    读取 RSS/Atom 订阅源。
    使用这个工具当用户想获取某个 RSS feed 的最新内容。

    Args:
        url: RSS/Atom feed URL

    Returns:
        最新条目列表的 JSON 字符串
    """
    try:
        # 用 requests 下载（绕过 venv 的 SSL 证书问题），再传给 feedparser 解析
        resp = requests.get(url, timeout=15, headers={"User-Agent": "agent-reach/1.0"})
        resp.raise_for_status()
        env = _build_env()
        r = subprocess.run(
            ["python3", "-c", "import sys, feedparser, json; d=feedparser.parse(sys.stdin.read()); entries=[{'title':e.title,'link':e.link,'summary':e.get('summary','')[:200]} for e in d.entries[:10]]; print(json.dumps(entries, ensure_ascii=False))"],
            input=resp.text,
            capture_output=True,
            text=True,
            env=env,
            timeout=20,
        )
        if r.returncode == 0:
            return _truncate(r.stdout)
        return f"解析失败: {r.stderr}"
    except Exception as e:
        return f"读取失败: {e}"


# ============ 全网搜索 ============

@tool
def search_web(query: str) -> str:
    """
    全网语义搜索。
    使用这个工具当用户想搜索最新的信息或多个来源的综合结果。

    Args:
        query: 搜索关键词

    Returns:
        搜索结果列表
    """
    ok, stdout, stderr = _run_cmd(["mcporter", "call", f'exa.web_search_exa(query: "{query}", numResults: 5)'], timeout=30)
    if ok:
        return _truncate(stdout)
    return f"搜索失败: {stderr}"


# ============ 小宇宙播客 ============

@tool
def transcribe_podcast(url: str) -> str:
    """
    转录小宇宙播客为文字。
    使用这个工具当用户想了解某个小宇宙播客的内容。

    Args:
        url: 小宇宙播客链接

    Returns:
        播客转录文本
    """
    env = _build_env()
    cfg = _load_config()
    if cfg.get("groq_api_key"):
        env["GROQ_API_KEY"] = cfg["groq_api_key"]

    output_file = f"/tmp/podcast_{int(__import__('time').time())}.txt"
    try:
        result = subprocess.run(
            ["bash", _PODCAST_SCRIPT, url, output_file],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        if result.returncode == 0 and Path(output_file).exists():
            text = Path(output_file).read_text(encoding="utf-8")
            return _truncate(text, 8000)
        return f"转录失败: {result.stderr}"
    except Exception as e:
        return f"转录失败: {str(e)}"


# ============ 工具列表 ============

tools = [
    search_twitter,
    read_webpage,
    get_youtube_transcript,
    search_bilibili,
    search_v2ex,
    read_rss,
    search_web,
    transcribe_podcast,
]
