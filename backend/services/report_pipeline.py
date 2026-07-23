from __future__ import annotations

from pydantic import BaseModel

from schemas.entity import ResolvedEntity
from schemas.release_diff import ReleaseDiffEvidence
from services.analysis_service import RepositoryAnalysisService
from services.comparison_service import RepositoryComparisonService
from services.evidence_service import RepositoryEvidenceService
from services.profile_service import RepositoryProfileService
from services.roadmap_service import RepositoryRoadmapService
from services.release_diff_service import ReleaseDiffService
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

    def build_evidence(self, entity: ResolvedEntity):
        return self.collector.collect(entity=entity, include_reddit=True)

    def generate_report(self, entity: ResolvedEntity, report_type: str):
        evidence = self.build_evidence(entity)
        if report_type == "profile":
            return self.profile.generate(evidence)
        if report_type == "roadmap":
            return self.roadmap.predict(evidence)
        if report_type in {"analysis", "project_health"}:
            return self.analysis.analyze(evidence)
        raise ValueError(f"Unsupported report_type: {report_type}")

    def generate_comparison(self, left: ResolvedEntity, right: ResolvedEntity):
        left_evidence = self.build_evidence(left)
        right_evidence = self.build_evidence(right)
        return self.comparison.compare(left_evidence, right_evidence)

    def generate_release_diff(self, entity: ResolvedEntity, old_tag: str, new_tag: str):
        evidence = self.build_evidence(entity)
        github_source = next((s for s in entity.sources if s.source == "github"), None)
        if not github_source:
            raise ValueError("Release diff requires github source")
        owner, repo = github_source.identifier.split("/", 1)
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
