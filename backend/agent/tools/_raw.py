# 原始数据源调用：Twitter/Reddit/Bilibili/V2EX/Web/YouTube/RSS/播客

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv()

import requests

from agent.tools._shared import (
    agent_reach_env,
    github,
    huggingface,
    load_agent_reach_config,
    run_agent_reach_cmd,
    truncate_text,
    parse_vtt,
    _PODCAST_SCRIPT,
)


# ── GitHub ──

def search_github_raw(query: str) -> list[dict[str, Any]]:
    """调用 GitHub Search API，返回原始 item 列表（按 stars 排序，最多 10 个）。"""
    response = github.client.get(
        "/search/repositories",
        params={"q": query, "sort": "stars", "order": "desc", "per_page": 10},
    )
    return response.json().get("items", []) or []


# ── HuggingFace ──

def search_huggingface_raw(query: str) -> list[dict[str, Any]]:
    """调用 HuggingFace Models API，返回原始 model 列表（按 downloads 排序，最多 5 个）。"""
    response = huggingface.session.get(
        f"{huggingface.BASE_URL}/api/models",
        params={"search": query, "limit": 5, "sort": "downloads", "direction": -1},
        timeout=20,
    )
    response.raise_for_status()
    return response.json() or []


# ── Twitter/X ──
# twitter-cli 当前不可用（HTTP 404），暂用 Tavily site:x.com 兜底。
# 待 twitter-cli 修复后可恢复两级 fallback 策略。

_twitter_search_cache: dict[str, str] = {}


def search_twitter_raw(query: str, limit: int = 10) -> str:
    """搜索 Twitter/X：通过 Tavily 搜索 site:x.com 获取推文内容。"""
    cache_key = f"{query}:{limit}"
    if cache_key in _twitter_search_cache:
        return _twitter_search_cache[cache_key]

    result = _search_twitter_via_web(query, limit)
    if not result:
        result = "搜索失败: Twitter/X web 搜索无结果（Tavily 未配置或无匹配）"
    _twitter_search_cache[cache_key] = result
    return result

def _search_twitter_via_web(query: str, limit: int) -> str:
    """通过 Tavily 搜索 site:x.com 获取 Twitter 讨论内容。"""
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        print("[twitter] TAVILY_API_KEY 未配置，无法搜索 Twitter")
        return ""

    try:
        search_query = f"site:x.com {query}"
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": search_query,
                "max_results": limit,
                "include_answer": False,
                "search_depth": "basic",
            },
            timeout=12,
        )
        if resp.status_code != 200:
            print(f"[twitter] Tavily HTTP {resp.status_code}")
            return ""

        results = resp.json().get("results", [])
        if not results:
            return ""

        parts = [f"Twitter/X 搜索结果: {query}", f"来源: Tavily site:x.com, 共 {len(results)} 条", ""]
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")
            parts.append(f"标题: {title}")
            parts.append(f"链接: {url}")
            if content:
                parts.append(f"摘要: {truncate_text(content, 500)}")
            parts.append("")

        return truncate_text("\n".join(parts), 8000)
    except Exception as exc:
        print(f"[twitter] web 搜索异常: {exc}")
        return ""


# ── twitter-cli（已停用，待修复后恢复） ──
# def _search_twitter_via_cli(query: str, limit: int) -> str:
#     cfg = load_agent_reach_config()
#     env = {}
#     if cfg.get("twitter_auth_token"):
#         env["TWITTER_AUTH_TOKEN"] = cfg["twitter_auth_token"]
#     if cfg.get("twitter_ct0"):
#         env["TWITTER_CT0"] = cfg["twitter_ct0"]
#     ok, stdout, stderr = run_agent_reach_cmd(
#         ["twitter", "search", query, "-n", str(limit), "--json"],
#         timeout=12, env=env,
#     )
#     if ok or stdout.strip():
#         return truncate_text(stdout, 8000)
#     return f"搜索失败: {stderr}"


# ── Reddit ──

def search_reddit_raw(query: str, limit: int = 10) -> str:
    """通过 OpenCLI 搜索 Reddit（复用 Chrome 登录态，桌面专用）。"""
    last_error = ""
    for search_query in _reddit_query_candidates(query)[:3]:
        ok, stdout, stderr = run_agent_reach_cmd(
            ["opencli", "reddit", "search", search_query, "-f", "yaml"],
            timeout=15,
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
    """Reddit 搜索候选词：primary term 优先，原始查询兜底。"""
    primary = _primary_reddit_term(query)
    candidates: list[str] = []
    if primary:
        candidates.append(primary)
    original = query.strip()
    if original and original != primary:
        candidates.append(original)
    return candidates


def _filter_reddit_yaml_output(output: str, query: str, limit: int) -> str:
    """过滤 Reddit 搜索结果：只保留核心实体词匹配的帖子。"""
    primary = _primary_reddit_term(query)
    if not primary:
        return output

    ambiguous = len(primary) <= 4 or primary in {"coze"}
    ai_keywords = {"ai", "agent", "agents", "chatbot", "bot", "llm", "workflow", "api"}

    blocks = re.split(r"\n(?=- id: )", output.strip())
    matched_blocks: list[str] = []
    for block in blocks:
        title = _extract_yaml_scalar(block, "title")
        subreddit = _extract_yaml_scalar(block, "subreddit")
        selftext = _extract_yaml_scalar(block, "selftext")
        haystack = f"{title} {subreddit} {selftext}".lower()
        if not re.search(rf"\b{re.escape(primary)}\b", haystack):
            continue
        if ambiguous and not any(kw in haystack for kw in ai_keywords):
            continue
        post_hint = _extract_yaml_scalar(block, "post_hint").lower()
        if ambiguous and post_hint == "image" and not selftext.strip():
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
    """读取 Reddit 帖子：先走 RSS 快速通道（~1.5s），内容不足再走 opencli（~6s）。"""
    clean_id = post_id.strip().strip("`")
    if clean_id.startswith("http"):
        match = re.search(r"/comments/([a-z0-9]+)", clean_id)
        if match:
            clean_id = match.group(1)
        else:
            clean_id = clean_id.rstrip("/").split("/")[-1]

    # 快速通道：RSS（帖子正文，无评论）
    rss_content = _read_reddit_rss(clean_id)
    if rss_content and len(rss_content) >= 200:
        return rss_content

    # 兜底：opencli（帖子 + 完整评论树）
    ok, stdout, stderr = run_agent_reach_cmd(
        ["opencli", "reddit", "read", clean_id, "-f", "yaml", "--limit", str(limit), "--depth", "2"],
        timeout=15,
    )
    if ok and stdout.strip():
        return truncate_text(stdout, 8000)
    if "tool-not-found" in (stderr or ""):
        return "读取失败: opencli 未安装"
    # 两个通道都失败时，优先返回 RSS 的部分内容而非 opencli 错误
    if rss_content:
        return rss_content
    return f"读取失败: {stderr or '未知错误'}"


def _read_reddit_rss(post_id: str) -> str:
    """通过 Reddit RSS 快速读取帖子正文（内部函数）。"""
    try:
        resp = requests.get(
            f"https://www.reddit.com/comments/{post_id}/.rss",
            headers={"User-Agent": "agent-reach/1.0 (research bot)"},
            timeout=8,
        )
        if resp.status_code != 200:
            return ""

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        entries = root.findall("atom:entry", ns)
        if not entries:
            return ""

        parts = []
        for entry in entries[:5]:
            title = entry.findtext("atom:title", "", ns)
            content = entry.findtext("atom:content", "", ns)
            author = entry.findtext("atom:author/atom:name", "", ns)
            content = re.sub(r"<[^>]+>", "", content).strip()
            if title:
                parts.append(f"标题: {title}")
            if author:
                parts.append(f"作者: {author}")
            if content:
                parts.append(truncate_text(content, 2000))
            parts.append("")

        return "\n".join(parts).strip()
    except Exception:
        return ""


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


# ── Bilibili ──

def search_bilibili_raw(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """通过 B站公开搜索 API 搜索视频。"""
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    try:
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

def read_bilibili_video_raw(bvid: str) -> str:
    """通过 B站公开 API 获取视频信息 + 热门评论，替代 Jina Reader 抓整页。"""
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    headers = {"User-Agent": ua, "Referer": "https://www.bilibili.com/"}

    # 1) 视频元信息（拿到 aid 用于评论接口）
    try:
        info_resp = requests.get(
            "https://api.bilibili.com/x/web-interface/view",
            params={"bvid": bvid},
            headers=headers,
            timeout=5,
        )
        info = info_resp.json().get("data", {})
    except Exception as exc:
        return f"B站视频信息获取失败: {exc}"

    title = info.get("title", "未知标题")
    desc = info.get("desc", "")
    owner = info.get("owner", {}).get("name", "未知UP主")
    view = info.get("stat", {}).get("view", 0)
    reply_count = info.get("stat", {}).get("reply", 0)
    aid = info.get("aid")

    parts = [
        f"标题: {title}",
        f"UP主: {owner}",
        f"播放: {view} | 评论数: {reply_count}",
    ]
    if desc:
        parts.append(f"简介: {desc}")

    # 2) 热门评论（需要 aid）
    if aid:
        try:
            cmt_resp = requests.get(
                "https://api.bilibili.com/x/v2/reply",
                params={"type": 1, "oid": aid, "sort": 1, "ps": 10},
                headers=headers,
                timeout=5,
            )
            replies = cmt_resp.json().get("data", {}).get("replies") or []
            if replies:
                parts.append("\n── 热门评论 ──")
                for r in replies[:10]:
                    name = r.get("member", {}).get("uname", "")
                    msg = r.get("content", {}).get("message", "")
                    likes = r.get("like", 0)
                    parts.append(f"[{name}] (👍{likes}): {msg}")
            else:
                parts.append("\n暂无评论")
        except Exception:
            parts.append("\n评论获取失败")

    return "\n".join(parts)


# ── V2EX（已停用，搜索 API 不可用，热门列表过滤命中率极低） ──
# def search_v2ex_raw(query: str, limit: int = 10) -> list[dict[str, Any]]:
#     try:
#         response = requests.get(
#             "https://www.v2ex.com/api/topics/hot.json",
#             headers={"User-Agent": "agent-reach/1.0"},
#             timeout=6,
#         )
#         payload = response.json()
#     except Exception as exc:
#         return [{"title": "V2EX 获取失败", "error": str(exc)}]
#     items = [item for item in payload or [] if query.lower() in (item.get("title") or "").lower()]
#     if not items:
#         return []
#     return [{"title": item.get("title"), "url": item.get("url"), "replies": item.get("replies"),
#              "node": item.get("node", {}).get("title"), "member": item.get("member", {}).get("username")}
#             for item in items[:limit]]


# ── Web ──
def search_web_raw(query: str, mode: str = "standard") -> list[str]:
    """混合 Web 搜索：根据 mode 选择搜索引擎，自动 fallback，
    返回 URL 列表。

    策略：
    - deep 模式：优先 Exa（语义搜索），fallback Tavily
    - quick/standard 模式：优先 Tavily（速度快），fallback Exa
    """
    exa_key = os.environ.get("EXA_API_KEY", "")
    tavily_key = os.environ.get("TAVILY_API_KEY", "")

    if mode == "deep":
        providers = [("exa", exa_key), ("tavily", tavily_key)]
    else:
        providers = [("tavily", tavily_key), ("exa", exa_key)]

    for name, api_key in providers:
        if not api_key:
            continue
        try:
            urls: list[str] = []
            if name == "tavily":
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "max_results": 3,
                        "include_answer": False,
                        "search_depth": "basic",
                    },
                    timeout=12,
                )
                if resp.status_code == 200:
                    urls = [r["url"] for r in resp.json().get("results", []) if r.get("url")]
                else:
                    print(f"[web_search] Tavily HTTP {resp.status_code}")
            elif name == "exa":
                resp = requests.post(
                    "https://api.exa.ai/search",
                    json={"query": query, "numResults": 3, "type": "auto"},
                    headers={"x-api-key": api_key, "Content-Type": "application/json"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    urls = [r["url"] for r in resp.json().get("results", []) if r.get("url")]
                else:
                    print(f"[web_search] Exa HTTP {resp.status_code}")

            if urls:
                print(f"[web_search] 使用 {name} 搜索成功: query={query}, 找到 {len(urls)} 个 URL")
                return urls
            print(f"[web_search] {name} 返回空结果，尝试下一个: query={query}")
        except Exception as e:
            print(f"[web_search] {name} 搜索异常: {e}")
            continue

    print(f"[web_search] 所有搜索引擎均失败或无 key: query={query}")
    return []


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
    """搜索 YouTube 视频：走 Tavily site:youtube.com（~2s），yt-dlp 太慢已停用。"""
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        return [{"title": "YouTube 搜索失败", "error": "TAVILY_API_KEY 未配置"}]

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": f"site:youtube.com {query}",
                "max_results": limit,
                "include_answer": False,
                "search_depth": "basic",
            },
            timeout=12,
        )
        if resp.status_code != 200:
            return [{"title": "YouTube 搜索失败", "error": f"Tavily HTTP {resp.status_code}"}]

        results = []
        for r in resp.json().get("results", []):
            url = r.get("url", "")
            if "youtube.com" not in url and "youtu.be" not in url:
                continue
            results.append({
                "title": r.get("title", ""),
                "url": url,
                "duration": None,
                "uploader": None,
            })
        return results[:limit] if results else [{"title": "YouTube 搜索无结果", "error": f"query={query}"}]
    except Exception as exc:
        return [{"title": "YouTube 搜索失败", "error": str(exc)}]


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
