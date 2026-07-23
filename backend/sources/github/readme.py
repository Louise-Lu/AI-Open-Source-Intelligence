from __future__ import annotations

from typing import Any

from .utils import decode_base64_content

import re

def clean_preview(text):

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    text = text.replace(
        "\n\n\n",
        "\n"
    )

    return text.strip()[:300]

class ReadmeTool:
    """README helper."""

    client: Any

    def get_readme(
        self,
        owner: str,
        repo: str
    ) -> str:

        response = self.client.get(
            f"/repos/{owner}/{repo}/readme"
        )

        payload = response.json()

        content = decode_base64_content(
            payload["content"]
        )


        # add_trace(
        #     tool_name="get_readme",
        #     tool_input={
        #         "owner": owner,
        #         "repo": repo
        #     },
        #     tool_output={
        #         "length": len(content),
        #         # "preview": clean_preview(content)
        #     }
        # )


        return content

