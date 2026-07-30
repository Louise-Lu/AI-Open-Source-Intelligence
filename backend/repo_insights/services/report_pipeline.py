from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from repo_insights.schemas.entity import RepositoryRef
from repo_insights.schemas.release_diff import ReleaseDiffEvidence
from repo_insights.services.analysis_service import RepositoryAnalysisService
from repo_insights.services.comparison_service import RepositoryComparisonService
from repo_insights.evidence.repo_evidence import RepositoryEvidenceService
from repo_insights.services.profile_service import RepositoryProfileService
from repo_insights.services.roadmap_service import RepositoryRoadmapService
from repo_insights.services.release_diff_service import ReleaseDiffService
from sources.github.client import GitHubAPI


class ReportPipeline:
    def __init__(self):
        self.collector = RepositoryEvidenceService()
        self.profile = RepositoryProfileService()
        self.roadmap = RepositoryRoadmapService()
        self.analysis = RepositoryAnalysisService()
        self.comparison = RepositoryComparisonService()
        self.release_diff = ReleaseDiffService()
        self.github = GitHubAPI()

    def build_evidence(self, entity: RepositoryRef):
        return self.collector.collect(entity=entity)

    def generate_report(self, entity: RepositoryRef, report_type: str):
        evidence = self.build_evidence(entity)
        if report_type == "profile":
            return self.profile.generate(evidence)
        if report_type == "roadmap":
            return self.roadmap.predict(evidence)
        if report_type in {"analysis", "project_health"}:
            return self.analysis.analyze(evidence)
        raise ValueError(f"Unsupported report_type: {report_type}")

    def generate_all(self, entity: RepositoryRef) -> dict:
        """收集一次证据，并发跑 profile + roadmap + analysis，返回组合结果。"""
        evidence = self.build_evidence(entity)

        tasks = {
            "profile": lambda: self.profile.generate(evidence),
            "roadmap": lambda: self.roadmap.predict(evidence),
            "analysis": lambda: self.analysis.analyze(evidence),
        }

        results: dict = {}
        errors: dict = {}

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {name: pool.submit(fn) for name, fn in tasks.items()}
            for name, future in futures.items():
                try:
                    results[name] = future.result()
                except Exception as exc:
                    print(f"[ReportPipeline] {name} 生成失败: {exc}")
                    errors[name] = str(exc)

        if errors:
            results["_errors"] = errors
        return results

    def generate_comparison(self, left: RepositoryRef, right: RepositoryRef):
        left_evidence = self.build_evidence(left)
        right_evidence = self.build_evidence(right)
        return self.comparison.compare(left_evidence, right_evidence)

    def generate_release_diff(self, entity: RepositoryRef, old_tag: str, new_tag: str):
        evidence = self.build_evidence(entity)
        owner, repo = entity.name.split("/", 1)
        releases = self.github.get_releases(owner, repo)
        old_release = next(release for release in releases if release["tag_name"] == old_tag)
        new_release = next(release for release in releases if release["tag_name"] == new_tag)
        diff_evidence = ReleaseDiffEvidence(
            old_tag=old_tag,
            new_tag=new_tag,
            old_body=old_release.get("body"),
            new_body=new_release.get("body"),
        )
        return self.release_diff.compare(diff_evidence)
