from services.evidence_service import RepositoryEvidenceService

# from llms.qwen import qwen_model
from llms.deepseek import deepseek_model
from prompts.roadmap import ROADMAP_PROMPT

from schemas.roadmap import RoadmapReport


class RepositoryRoadmapService:

    def __init__(self):
        self.evidence_service = RepositoryEvidenceService()

    # -----------------------------------------------
    # 证据分层整理函数（直接放在类内或模块内均可）
    # -----------------------------------------------
    @staticmethod
    def format_roadmap_evidence(evidence):
        """将 IntelligenceEvidence 整理成三层情报文本，供 LLM 阅读"""
        github_evidence = evidence.github
        if not github_evidence:
            return "无 GitHub 数据"

        repo = github_evidence.repository
        planning = github_evidence.planning
        discussions = github_evidence.discussions
        commits = github_evidence.commit_activity
        prs = github_evidence.pull_requests
        readme = github_evidence.readme

        parts = []

        # 基础画像
        parts.append(
            f"项目：{repo.full_name if repo else '未知'}"
        )
        parts.append(
            f"描述：{repo.description if repo else '无'}"
        )
        parts.append(
            f"语言：{repo.language if repo else '未知'} | "
            f"Stars：{repo.stars if repo else 0} | "
            f"License：{repo.license if repo else '未知'}"
        )

        # 显性规划
        parts.append("\n【显性规划】")
        if planning:
            if planning.roadmap_text:
                parts.append(
                    f"ROADMAP.md 摘要：\n{planning.roadmap_text[:1500]}"
                )
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

        # 隐性动态
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

        # 社区脉搏
        parts.append("\n【社区脉搏】")
        if discussions and discussions.hot_topics:
            parts.append("近期热门讨论：")
            for topic in discussions.hot_topics:
                parts.append(f"  - {topic}")
        else:
            parts.append("近期热门讨论：无")

        # 辅助上下文：README 开头
        if readme:
            parts.append(f"\n【README 摘要】\n{readme[:1000]}")

        return "\n".join(parts)

    # -----------------------------------------------
    # 主预测方法（只改 evidence 转文本这一步）
    # -----------------------------------------------
    def predict(self, owner: str, repo: str) -> RoadmapReport:
        # ① 收集证据
        evidence = self.evidence_service.collect(owner, repo)

        # ② 整理成分层文本
        evidence_text = self.format_roadmap_evidence(evidence)

        # ③ 拼装最终 prompt
        prompt = f"""
{ROADMAP_PROMPT}

Repository Evidence:

{evidence_text}
"""

        # ④ 绑定结构化输出的模型
        llm = deepseek_model.with_structured_output(RoadmapReport)

        # ⑤ 调用
        try:
            roadmap = llm.invoke(prompt)

            print("==========  DEBUG ==========")
            print(roadmap)
            print(type(roadmap))
            print("===================================")

            return roadmap

        except Exception as e:
            print("========== roadmap ERROR ==========")
            print(e)
            print("===================================")
            raise