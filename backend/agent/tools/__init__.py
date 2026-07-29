# 将 Discovery 和 Capability 工具统一暴露，保持向后兼容：from agent.tools import TOOLS

from agent.tools.discovery import (
    github_search,
    huggingface_search,
    community_search,
    web_search,
    youtube_search,
)
from agent.tools.capability import (
    github_project_profile,
    github_project_health,
    github_release_summary,
    github_ecosystem,
    huggingface_model_profile,
    community_reader,
    webpage_reader,
    youtube_transcript,
    rss_reader,
    podcast_transcript,
)

TOOLS = [
    # Discovery
    github_search,
    huggingface_search,
    community_search,
    web_search,
    youtube_search,

    # GitHub Capability
    github_project_profile,
    github_project_health,
    github_release_summary,
    github_ecosystem,

    # HuggingFace Capability
    huggingface_model_profile,

    # Community / Web / Video Capability
    community_reader,
    webpage_reader,
    youtube_transcript,
    rss_reader,
    podcast_transcript,
]
