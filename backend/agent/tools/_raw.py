# 原始数据源调用：Twitter/Reddit/Bilibili/V2EX/Web/YouTube/RSS/播客

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import requests

from agent.tools._shared import (
    agent_reach_env,
    load_agent_reach_config,
    run_agent_reach_cmd,
    truncate_text,
    parse_vtt,
    _PODCAST_SCRIPT,
)

# ── Twitter/X ──

def search_twitter_raw(query: str, limit: int = 10) -> str:
    """调用 twitter-cli 搜索 Twitter/X。"""
    cfg = load_agent_reach_config()  # 读取 ~/.agent-reach/config.yaml

    # 读取 Twitter 凭据并设置环境变量
    env = {}
    if cfg.get("twitter_auth_token"):
        env["TWITTER_AUTH_TOKEN"] = cfg["twitter_auth_token"]
    if cfg.get("twitter_ct0"):
        env["TWITTER_CT0"] = cfg["twitter_ct0"]

    ok, stdout, stderr = run_agent_reach_cmd(
        ["twitter", "search", query, "-n", str(limit), "--json"],
        timeout=12,
        env=env,
    )
    if ok or stdout.strip():
        return truncate_text(stdout, 8000)
    return f"搜索失败: {stderr}"


# ── Reddit ──

def search_reddit_raw(query: str, limit: int = 10) -> str:
    """通过 OpenCLI 搜索 Reddit（复用 Chrome 登录态，桌面专用）。"""
    last_error = ""
    for search_query in _reddit_query_candidates(query)[:3]:
        ok, stdout, stderr = run_agent_reach_cmd(
            ["opencli", "reddit", "search", search_query, "-f", "yaml"],
            timeout=25,
        )
        # opencli 成功但无结果（Reddit 对中文关键词支持弱）→ 继续尝试英文候选词
        if ok:
            stripped = stdout.strip()
            if stripped and stripped != "[]":
                filtered = _filter_reddit_yaml_output(stripped, search_query, limit)
                if filtered:
                    return truncate_text(filtered, 8000)
                continue
            continue
        last_error = stderr or "未知错误"
        if "tool-not-found" in last_error:
            return "搜索失败: opencli 未安装，运行 agent-reach install --channels opencli"
    return f"搜索失败: {last_error}" if last_error else ""


def _reddit_query_candidates(query: str) -> list[str]:
    """Reddit 搜索候选词：primary term 优先（精准、召回率高），长查询兜底。

    Reddit 搜索对多词查询做 OR 匹配，"CrewAI review sentiment 2024 2025"
    会命中所有含 review/2025 的帖子（电影评论等），全部被过滤器丢弃。
    所以把最精准的 primary term 放第一位，命中即返回，不浪费时间。
    """
    primary = _primary_reddit_term(query)
    candidates: list[str] = []

    # 1. primary term 最精准，优先尝试
    if primary:
        candidates.append(primary)

    # 2. 原始查询作为兜底（用户可能输入了特殊修饰词）
    original = query.strip()
    if original:
        candidates.append(original)

    # 3. ascii 拼接词（去掉年份等非字母 token）
    ascii_terms = re.findall(r"[A-Za-z][A-Za-z0-9_.-]*", query)
    if ascii_terms:
        ascii_query = " ".join(ascii_terms)
        candidates.append(ascii_query)

    # 4. primary + 上下文词扩展
    if primary and len(ascii_terms) > 1:
        candidates.extend(
            [
                f"{primary} AI",
                f"{primary} agent",
                f"{primary} review",
            ]
        )

    return list(dict.fromkeys(item for item in candidates if item))


def _filter_reddit_yaml_output(output: str, query: str, limit: int) -> str:
    """过滤 Reddit 搜索结果：只硬匹配核心实体词，避免把 sentiment/year 当成必需词。"""
    primary = _primary_reddit_term(query)
    if not primary:
        return output

    blocks = re.split(r"\n(?=- id: )", output.strip())
    matched_blocks: list[str] = []
    for block in blocks:
        title = _extract_yaml_scalar(block, "title")
        subreddit = _extract_yaml_scalar(block, "subreddit")
        selftext = _extract_yaml_scalar(block, "selftext")
        haystack = f"{title} {subreddit} {selftext}".lower()
        if not re.search(rf"\b{re.escape(primary)}\b", haystack):
            continue
        # Coze 这类短词容易误命中 cozy/狐狸/家居图片帖，需要 AI 上下文；CrewAI 这类专有词不强制。
        if _is_ambiguous_reddit_term(primary) and not _has_reddit_ai_context(haystack):
            continue
        if _looks_like_image_only_reddit_post(block) and _is_ambiguous_reddit_term(primary):
            continue
        matched_blocks.append(block.strip())

    return "\n".join(matched_blocks[:limit])


def parse_reddit_posts(yaml_output: str) -> list[dict[str, Any]]:
    """把 opencli reddit search 的 YAML 输出解析成独立的帖子列表。

    每个 dict 包含: id, title, subreddit, author, score, comments, url, selftext。
    """
    blocks = re.split(r"\n(?=- id: )", yaml_output.strip())
    posts: list[dict[str, Any]] = []
    for block in blocks:
        block = block.strip()
        if not block.startswith("- id:"):
            continue
        # YAML 列表项第一行是 "- id: xxx"，去掉 "- " 前缀让 _extract_yaml_scalar 能匹配
        block = block.replace("- id:", "id:", 1)
        post_id = _extract_yaml_scalar(block, "id")
        if not post_id:
            continue
        posts.append(
            {
                "id": post_id,
                "title": _extract_yaml_scalar(block, "title"),
                "subreddit": _extract_yaml_scalar(block, "subreddit"),
                "author": _extract_yaml_scalar(block, "author"),
                "score": _extract_yaml_scalar(block, "score"),
                "comments": _extract_yaml_scalar(block, "comments"),
                "url": _extract_yaml_scalar(block, "url"),
                "selftext": _extract_yaml_scalar(block, "selftext"),
            }
        )
    return posts


def read_reddit_post_raw(post_id: str, limit: int = 10) -> str:
    """通过 opencli reddit read 读取单个 Reddit 帖子及其评论。"""
    # 支持传入完整 URL 或纯 post-id
    clean_id = post_id.strip().strip("`")
    if clean_id.startswith("http"):
        # 从 URL 提取 post-id: https://www.reddit.com/r/xxx/comments/1txlb3n/...
        match = re.search(r"/comments/([a-z0-9]+)", clean_id)
        if match:
            clean_id = match.group(1)
        else:
            clean_id = clean_id.rstrip("/").split("/")[-1]

    ok, stdout, stderr = run_agent_reach_cmd(
        ["opencli", "reddit", "read", clean_id, "-f", "yaml", "--limit", str(limit), "--depth", "2"],
        timeout=25,
    )
    if ok and stdout.strip():
        return truncate_text(stdout, 8000)
    if "tool-not-found" in (stderr or ""):
        return "读取失败: opencli 未安装"
    return f"读取失败: {stderr or '未知错误'}"


def _primary_reddit_term(query: str) -> str:
    """提取 Reddit 搜索的核心实体词，过滤 community/sentiment/year 等修饰词。"""
    ignored = {
        "community",
        "sentiment",
        "review",
        "reviews",
        "problem",
        "problems",
        "complaint",
        "complaints",
        "activity",
        "recent",
        "latest",
        "really",
        "using",
        "user",
        "users",
        "feedback",
        "vs",
        "and",
        "the",
        "for",
        "with",
    }
    for term in re.findall(r"[A-Za-z][A-Za-z0-9_.-]*", query):
        lower = term.lower()
        if lower in ignored or re.fullmatch(r"20\d{2}", lower):
            continue
        return lower
    return ""


def _is_ambiguous_reddit_term(term: str) -> bool:
    """短词更容易误召回普通词或图片帖。"""
    return len(term) <= 4 or term in {"coze"}


def _looks_like_image_only_reddit_post(block: str) -> bool:
    """识别 Reddit 图片帖，避免作为产品社区讨论证据。"""
    post_hint = _extract_yaml_scalar(block, "post_hint").lower()
    selftext = _extract_yaml_scalar(block, "selftext").strip()
    return post_hint == "image" and not selftext


def _extract_yaml_scalar(block: str, key: str) -> str:
    """从 opencli 的 YAML 文本中提取简单标量字段，支持 block scalar (>- / > / |- / |)。"""
    match = re.search(rf"^\s*{re.escape(key)}:\s*(.*)$", block, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    # Block scalar: 后续缩进行是实际内容
    if value in (">-", ">", "|-", "|"):
        lines = block.split("\n")
        start_idx = None
        for i, line in enumerate(lines):
            if re.search(rf"^\s*{re.escape(key)}:\s*", line):
                start_idx = i + 1
                break
        if start_idx is None:
            return ""
        collected: list[str] = []
        for line in lines[start_idx:]:
            if line.strip() == "":
                continue
            if not line.startswith("  "):
                break
            collected.append(line.strip())
        return " ".join(collected)
    return value.strip(" '\"")


def _has_reddit_ai_context(text: str) -> bool:
    """避免短词命中狐狸/家居/图片帖，只保留 AI 产品相关讨论。"""
    context_terms = {
        "ai",
        "agent",
        "agents",
        "chatbot",
        "bot",
        "llm",
        "workflow",
        "automation",
        "bytedance",
        "coze.com",
        "no-code",
        "nocode",
        "review",
        "tool",
        "api",
    }
    return any(term in text for term in context_terms)


# ── Bilibili ──

def search_bilibili_raw(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """搜索 B站视频；bili-cli 不可用时用公开 API 兜底。"""
    ok, stdout, _ = run_agent_reach_cmd(
        ["bili", "search", query, "--type", "video", "-n", str(limit)],
        timeout=8,
    )
    if ok and stdout.strip():
        return [{"title": line, "raw": line} for line in stdout.splitlines()[:limit]]

    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    try:
        requests.get("https://www.bilibili.com/", headers={"User-Agent": ua}, timeout=5)
        response = requests.get(
            "https://api.bilibili.com/x/web-interface/search/all/v2",
            params={"keyword": query, "page": 1},
            headers={"User-Agent": ua, "Referer": "https://www.bilibili.com/"},
            timeout=5,
        )
        payload = response.json()
    except Exception as exc:
        return [{"title": "B站搜索失败", "error": str(exc)}]

    results: list[dict[str, Any]] = []
    for group in payload.get("data", {}).get("result", []) or []:
        if group.get("result_type") != "video":
            continue
        for item in group.get("data", [])[:limit]:
            title = (item.get("title") or "").replace('<em class="keyword">', "").replace("</em>", "")
            results.append(
                {
                    "title": title,
                    "bvid": item.get("bvid"),
                    "url": f"https://www.bilibili.com/video/{item.get('bvid')}" if item.get("bvid") else "",
                    "play": item.get("play"),
                    "up": item.get("author"),
                }
            )
    return results[:limit]


# ── V2EX ──

def search_v2ex_raw(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """获取 V2EX 热门主题；V2EX 搜索 API 已不可用，所以按标题做本地过滤。"""
    try:
        response = requests.get(
            "https://www.v2ex.com/api/topics/hot.json",
            headers={"User-Agent": "agent-reach/1.0"},
            timeout=6,
        )
        payload = response.json()
    except Exception as exc:
        return [{"title": "V2EX 获取失败", "error": str(exc)}]

    items = [
        item
        for item in payload or []
        if query.lower() in (item.get("title") or "").lower()
    ]
    if not items:
        return []

    return [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "replies": item.get("replies"),
            "node": item.get("node", {}).get("title"),
            "member": item.get("member", {}).get("username"),
        }
        for item in items[:limit]
    ]


# ── Web ──

def read_webpage_raw(url: str) -> str:
    """通过 Jina Reader 读取网页正文。"""
    try:
        clean_url = str(url or "").strip().strip("`")
        response = requests.get(f"https://r.jina.ai/{clean_url}", timeout=12)
        return truncate_text(_clean_jina_reader_text(response.text), 8000)
    except Exception as exc:
        return f"读取失败: {exc}"


def _clean_jina_reader_text(text: str) -> str:
    """清理 Jina Reader 仍可能保留的图片、导航和无意义链接噪声。"""
    value = str(text or "")
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", value)
    value = re.sub(r"\[[^\]]*\]\((?:javascript:|blob:)[^)]+\)", " ", value)
    value = re.sub(r"blob:http://[^\s)]+", " ", value)
    value = re.sub(r"javascript:;", " ", value)
    value = re.sub(r"`?https?://[^\s`<>)]+\.(?:png|jpg|jpeg|gif|webp|svg)(?:\?[^\s`<>)]+)?`?", " ", value, flags=re.I)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def search_web_raw(query: str) -> str:
    """通过 mcporter + Exa 搜索 Web。"""
    ok, stdout, stderr = run_agent_reach_cmd(
        ["mcporter", "call", f'exa.web_search_exa(query: "{query}", numResults: 3)'],
        timeout=12,
    )
    if ok:
        return truncate_text(stdout, 8000)
    return f"搜索失败: {stderr}"


# ── YouTube ──

def youtube_transcript_raw(video_url: str) -> str:
    """用 yt-dlp 获取 YouTube 字幕；没有字幕时退回视频元信息。"""
    ok, _, _ = run_agent_reach_cmd(
        [
            "yt-dlp",
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang",
            "zh-Hans,zh,en",
            "--skip-download",
            "-o",
            "/tmp/%(id)s",
            video_url,
        ],
        timeout=60,
    )
    if ok:
        video_id = video_url.split("v=")[-1].split("&")[0] if "v=" in video_url else video_url.split("/")[-1]
        vtt_files = list(Path("/tmp").glob(f"{video_id}*.vtt"))
        if vtt_files:
            return truncate_text(parse_vtt(vtt_files[0].read_text(encoding="utf-8")), 8000)

    ok, stdout, stderr = run_agent_reach_cmd(["yt-dlp", "--dump-json", video_url], timeout=60)
    if not ok:
        return f"获取失败: {stderr}"
    data = json.loads(stdout)
    return json.dumps(
        {
            "title": data.get("title"),
            "uploader": data.get("uploader"),
            "duration": data.get("duration"),
            "description": truncate_text(data.get("description", ""), 2000),
            "subtitles": "未找到字幕，已返回视频元信息",
        },
        ensure_ascii=False,
    )


def search_youtube_raw(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """用 yt-dlp 搜索 YouTube 视频。"""
    ok, stdout, stderr = run_agent_reach_cmd(
        ["yt-dlp", "--dump-json", f"ytsearch{limit}:{query}"],
        timeout=60,
    )
    if not ok:
        return [{"title": "YouTube 搜索失败", "error": stderr}]

    results = []
    for line in stdout.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        video_id = item.get("id")
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("webpage_url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else ""),
                "duration": item.get("duration"),
                "uploader": item.get("uploader"),
            }
        )
    return results[:limit]


# ── RSS ──

def read_rss_raw(url: str) -> str:
    """读取 RSS/Atom 订阅源。"""
    try:
        response = requests.get(url, timeout=8, headers={"User-Agent": "agent-reach/1.0"})
        response.raise_for_status()
        env = agent_reach_env()
        result = subprocess.run(
            [
                "python3",
                "-c",
                (
                    "import sys, feedparser, json; "
                    "d=feedparser.parse(sys.stdin.read()); "
                    "entries=[{'title':e.title,'link':e.link,'summary':e.get('summary','')[:200]} for e in d.entries[:10]]; "
                    "print(json.dumps(entries, ensure_ascii=False))"
                ),
            ],
            input=response.text,
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        if result.returncode == 0:
            return truncate_text(result.stdout, 8000)
        return f"解析失败: {result.stderr}"
    except Exception as exc:
        return f"读取失败: {exc}"


# ── Podcast ──

def transcribe_podcast_raw(url: str) -> str:
    """转录小宇宙播客。"""
    cfg = load_agent_reach_config()
    env = agent_reach_env()
    if cfg.get("groq_api_key"):
        env["GROQ_API_KEY"] = cfg["groq_api_key"]

    output_file = f"/tmp/podcast_{__import__('time').time_ns()}.txt"
    try:
        result = subprocess.run(
            ["bash", _PODCAST_SCRIPT, url, output_file],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        if result.returncode == 0 and Path(output_file).exists():
            return truncate_text(Path(output_file).read_text(encoding="utf-8"), 8000)
        return f"转录失败: {result.stderr}"
    except Exception as exc:
        return f"转录失败: {exc}"
