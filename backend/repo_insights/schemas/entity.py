"""Legacy 实体模型 — 仅用于 GitHub 仓库场景。"""

from __future__ import annotations


class RepositoryRef:
    """GitHub 仓库引用 — repo_insights 专用。"""

    __slots__ = ("name", "aliases")

    def __init__(self, name: str, aliases: list[str] | None = None):
        self.name = name
        self.aliases = aliases or [name]
