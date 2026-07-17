from __future__ import annotations

from typing import Any
from agent.trace import add_trace


class DiscussionTool:
    """
    获取仓库社区讨论信号

    返回：
    - hot_topics: list[dict]
        {
            "title": str,
            "has_official_answer": bool,
            "maintainer_involved": bool
        }
    """

    client: Any

    def get_discussion_signals(
        self,
        owner: str,
        repo: str
    ) -> dict[str, Any]:
        query = """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            discussions(first: 10, orderBy: {field: UPDATED_AT, direction: DESC}) {
              nodes {
                title
                answerChosenAt
                comments(last: 3) {
                  nodes {
                    author {
                      login
                    }
                  }
                }
                author {
                  login
                }
              }
            }
          }
        }
        """

        hot_topics = []
        try:
            resp = self.client.post(
                "/graphql",
                json={"query": query, "variables": {"owner": owner, "repo": repo}},
            )
            data = resp.json()
            discussions = (
                data.get("data", {})
                .get("repository", {})
                .get("discussions", {})
                .get("nodes", [])
            )
            if discussions:
                for d in discussions:
                    title = d.get("title", "")
                    has_official_answer = d.get("answerChosenAt") is not None
                    # 简单判断：讨论的作者、最近评论者中是否包含 repo owner
                    # 这里用字符串检查，你也可预先获取维护者名单做精确匹配
                    maintainer_involved = False
                    recent_authors = set()
                    author_login = d.get("author", {}).get("login")
                    if author_login:
                        recent_authors.add(author_login)
                    for comment in d.get("comments", {}).get("nodes", []):
                        comment_author = (
                            comment.get("author", {}).get("login")
                        )
                        if comment_author:
                            recent_authors.add(comment_author)
                    if owner in recent_authors:
                        maintainer_involved = True

                    hot_topics.append(
                        {
                            "title": title,
                            "has_official_answer": has_official_answer,
                            "maintainer_involved": maintainer_involved,
                        }
                    )
        except Exception:
            pass

        result = {"hot_topics": hot_topics}

        add_trace(
            tool_name="get_discussion_signals",
            tool_input={
                "owner": owner,
                "repo": repo,
            },
            tool_output=result,
        )

        return result