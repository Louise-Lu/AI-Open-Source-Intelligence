from __future__ import annotations

from typing import Any

from services.analysis_service import RepositoryAnalysisService
from services.comparison_service import RepositoryComparisonService
from services.profile_service import RepositoryProfileService
from services.roadmap_service import RepositoryRoadmapService


class ReportOrchestrator:
    def __init__(self):
        self.profile = RepositoryProfileService()
        self.roadmap = RepositoryRoadmapService()
        self.analysis = RepositoryAnalysisService()
        self.comparison = RepositoryComparisonService()

    def generate_single_project(self, owner: str, repo: str, reports: list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {}

        if "profile" in reports:
            payload["profile"] = self.profile.generate(owner, repo).model_dump()
        if "analysis" in reports or "project_health" in reports:
            payload["analysis"] = self.analysis.analyze(owner, repo)
        if "roadmap" in reports:
            payload["roadmap"] = self.roadmap.predict(owner, repo).model_dump()
        if "recommendation" in reports and "analysis" not in payload:
            payload["analysis"] = self.analysis.analyze(owner, repo)
        if "release_diff" in reports:
            payload["release_diff"] = self.analysis.analyze(owner, repo)

        return payload

    def generate_comparison(self, left: dict[str, str], right: dict[str, str], reports: list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {}

        if "comparison" in reports:
            payload["comparison"] = self.comparison.compare(
                left["owner"],
                left["repo"],
                right["owner"],
                right["repo"],
            ).model_dump()

        return payload
