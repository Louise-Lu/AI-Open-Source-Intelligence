from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from evidence import EvidenceBuilder
from router.entity_extractor import EntityExtractor
from router.entity_resolver import EntityResolver
from schemas.entity import EntitySource
from prompts.roadmap import ROADMAP_PROMPT
from services.report_orchestrator import ReportOrchestrator


class HuggingFaceSupportTests(unittest.TestCase):
    def test_build_huggingface_evidence_from_raw(self) -> None:
        builder = EvidenceBuilder()
        evidence = builder.build_huggingface_evidence(
            {
                "downloads": 1000000,
                "likes": 5000,
                "pipeline_tag": "text-generation",
                "tags": ["transformers", "llm"],
                "lastModified": "2026-07-01T00:00:00.000Z",
            }
        )

        self.assertIsNotNone(evidence)
        self.assertEqual(evidence.downloads, 1000000)
        self.assertEqual(evidence.likes, 5000)
        self.assertEqual(evidence.pipeline_tag, "text-generation")
        self.assertEqual(evidence.tags, ["transformers", "llm"])
        self.assertEqual(evidence.last_modified, "2026-07-01T00:00:00.000Z")

    def test_roadmap_prompt_mentions_huggingface_signals(self) -> None:
        self.assertIn("HuggingFace Signals", ROADMAP_PROMPT)
        self.assertIn("GitHub engineering activity", ROADMAP_PROMPT)

    def test_entity_extractor_labels_entity_type(self) -> None:
        extracted = EntityExtractor._rule_based_extract("Qwen怎么样")
        self.assertEqual(extracted["entities"][0]["name"], "Qwen")

    @patch.object(EntityResolver, "_llm_resolve", return_value=None)
    def test_entity_resolver_resolves_known_entities(self, _mock_llm) -> None:
        langgraph = EntityResolver().resolve({"name": "LangGraph"})
        qwen = EntityResolver().resolve({"name": "Qwen"})
        unknown = EntityResolver().resolve({"name": "未知项目abc"})

        self.assertEqual(
            langgraph.sources,
            [EntitySource(source="github", identifier="langchain-ai/langgraph")],
        )

        self.assertEqual(
            qwen.sources,
            [
                EntitySource(source="github", identifier="QwenLM/Qwen"),
                EntitySource(source="huggingface", identifier="Qwen/Qwen2.5-7B"),
            ],
        )

        self.assertEqual(unknown.sources, [])

    @patch("services.report_orchestrator.RepositoryProfileService")
    @patch("services.report_orchestrator.RepositoryAnalysisService")
    @patch("services.report_orchestrator.RepositoryRoadmapService")
    def test_orchestrator_passes_huggingface_model_id(
        self,
        roadmap_cls: MagicMock,
        analysis_cls: MagicMock,
        profile_cls: MagicMock,
    ) -> None:
        profile_instance = profile_cls.return_value
        analysis_instance = analysis_cls.return_value
        roadmap_instance = roadmap_cls.return_value

        profile_instance.generate.return_value.model_dump.return_value = {"profile": True}
        analysis_instance.analyze.return_value = "analysis"
        roadmap_instance.predict.return_value.model_dump.return_value = {"roadmap": True}

        orchestrator = ReportOrchestrator()
        entity = EntityResolver().resolve({"name": "Qwen"})
        payload = orchestrator.generate_single_project(
            entity,
            ["profile", "analysis", "roadmap"],
        )

        profile_instance.generate.assert_called_once_with(entity=entity)
        analysis_instance.analyze.assert_called_once_with(entity=entity)
        roadmap_instance.predict.assert_called_once_with(entity=entity)
        self.assertEqual(payload["profile"], {"profile": True})
        self.assertEqual(payload["analysis"], "analysis")
        self.assertEqual(payload["roadmap"], {"roadmap": True})


if __name__ == "__main__":
    unittest.main()
