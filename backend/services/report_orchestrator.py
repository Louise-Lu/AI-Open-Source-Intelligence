from __future__ import annotations

from typing import Any

from schemas.entity import ResolvedEntity
from services.report_pipeline import ReportPipeline


class ReportOrchestrator:
    def __init__(self):
        self.pipeline = ReportPipeline()

    def generate_single_project(self, entity: ResolvedEntity, reports: list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for report_type in reports:
            if report_type in {"profile", "roadmap", "analysis", "project_health"}:
                key = "analysis" if report_type == "project_health" else report_type
                if key not in payload:
                    result = self.pipeline.generate_report(entity, key)
                    payload[key] = result.model_dump() if hasattr(result, "model_dump") else result
        return payload

    def generate_comparison(self, left: ResolvedEntity, right: ResolvedEntity, reports: list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if "comparison" in reports:
            payload["comparison"] = self.pipeline.generate_comparison(left, right).model_dump()
        return payload
