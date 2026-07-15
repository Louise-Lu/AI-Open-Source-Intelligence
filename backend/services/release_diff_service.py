from __future__ import annotations

from tools.github.client import GitHubAPI

from llms.qwen import qwen_model

from prompts.release_diff import RELEASE_DIFF_PROMPT

from schemas.release_diff import ReleaseDiffEvidence


class ReleaseDiffService:

    def __init__(self):
        self.github = GitHubAPI()

    def compare(
        self,
        owner: str,
        repo: str,
        old_tag: str,
        new_tag: str,
    ) -> str:

        releases = self.github.get_releases(owner, repo)

        old_release = next(
            release
            for release in releases
            if release["tag_name"] == old_tag
        )

        new_release = next(
            release
            for release in releases
            if release["tag_name"] == new_tag
        )

        evidence = ReleaseDiffEvidence(
            old_tag=old_tag,
            new_tag=new_tag,
            old_body=old_release.get("body"),
            new_body=new_release.get("body"),
        )

        response = qwen_model.invoke(
            RELEASE_DIFF_PROMPT
            + "\n\n"
            + evidence.model_dump_json(indent=2)
        )

        return response.content