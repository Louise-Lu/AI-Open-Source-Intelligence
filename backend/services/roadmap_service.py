from evidence import IntelligenceEvidence
from llms.deepseek import deepseek_model
from prompts.roadmap import ROADMAP_PROMPT
from schemas.roadmap import RoadmapReport


class RepositoryRoadmapService:
    @staticmethod
    def format_roadmap_evidence(evidence: IntelligenceEvidence):
        github = evidence.github
        if not github:
            return "无 GitHub 数据"
        reddit = evidence.reddit
        huggingface = evidence.huggingface

        repo = github.repository
        planning = github.planning
        discussions = github.discussions
        commits = github.commit_activity
        prs = github.pull_requests
        readme = github.readme

        parts = []
        parts.append(f"项目：{repo.full_name if repo else '未知'}")
        parts.append(f"描述：{repo.description if repo else '无'}")
        parts.append(
            f"语言：{repo.language if repo else '未知'} | "
            f"Stars：{repo.stars if repo else 0} | "
            f"License：{repo.license if repo else '未知'}"
        )
        parts.append("\n【显性规划】")
        if planning:
            if planning.roadmap_text:
                parts.append(f"ROADMAP.md 摘要：\n{planning.roadmap_text[:1500]}")
            else:
                parts.append("ROADMAP.md：无")
            if planning.milestones:
                ms_lines = []
                for m in planning.milestones:
                    title = m.get("title", "")
                    due = m.get("due_on", "未设截止")
                    prog = m.get("progress_percent", "?")
                    ms_lines.append(f"  - {title} (截止: {due}, 完成度: {prog}%)")
                parts.append("开放里程碑：\n" + "\n".join(ms_lines))
            else:
                parts.append("开放里程碑：无")
            if planning.enhancement_issues:
                parts.append("近期增强/提案 Issue：")
                for issue in planning.enhancement_issues:
                    parts.append(f"  - {issue}")
            else:
                parts.append("近期增强/提案 Issue：无")
        else:
            parts.append("无规划数据")
        parts.append("\n【隐性动态】")
        if commits:
            parts.append(
                f"近30天提交：{commits.commits_last_30_days} 次，"
                f"近90天提交：{commits.commits_last_90_days} 次"
            )
            parts.append(f"活跃贡献者数：{commits.active_contributors_count}")
        else:
            parts.append("提交活跃度数据缺失")
        if prs:
            recent_pr_titles = [pr.title for pr in prs[:5] if pr.title]
            if recent_pr_titles:
                parts.append("近期 PR 标题：")
                for t in recent_pr_titles:
                    parts.append(f"  - {t}")
            else:
                parts.append("近期无 PR 数据")
        else:
            parts.append("PR 数据缺失")
        parts.append("\n【社区脉搏】")
        if discussions and discussions.hot_topics:
            parts.append("近期热门讨论：")
            for topic in discussions.hot_topics:
                parts.append(f"  - {topic}")
        else:
            parts.append("近期热门讨论：无")
        parts.append("\n【Community Signals】")
        if reddit and reddit.posts:
            parts.append("Reddit 相关帖子：")
            for post in reddit.posts[:5]:
                parts.append(f"  - {post}")
            parts.append(f"Reddit 提及次数：{reddit.mentions}")
        else:
            parts.append("Reddit 相关帖子：无")
        parts.append("\n【HuggingFace Signals】")
        if huggingface:
            parts.append(f"Downloads：{huggingface.downloads} | Likes：{huggingface.likes}")
            if huggingface.pipeline_tag:
                parts.append(f"Pipeline：{huggingface.pipeline_tag}")
            if huggingface.tags:
                parts.append("Tags：" + ", ".join(huggingface.tags[:10]))
            if huggingface.last_modified:
                parts.append(f"Last Modified：{huggingface.last_modified}")
        else:
            parts.append("HuggingFace 信号：无")
        if readme:
            parts.append(f"\n【README 摘要】\n{readme[:1000]}")
        return "\n".join(parts)

    def predict(self, evidence: IntelligenceEvidence) -> RoadmapReport:
        evidence_text = self.format_roadmap_evidence(evidence)
        prompt = f"""
{ROADMAP_PROMPT}

Repository Evidence:

{evidence_text}
"""
        llm = deepseek_model.with_structured_output(RoadmapReport)
        return llm.invoke(prompt)
