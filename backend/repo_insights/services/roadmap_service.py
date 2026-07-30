from evidence import IntelligenceEvidence
from llms.deepseek import deepseek_structured_model
from repo_insights.prompts.roadmap import ROADMAP_PROMPT
from repo_insights.schemas.roadmap import RoadmapReport


class RepositoryRoadmapService:
    @staticmethod
    def format_roadmap_evidence(evidence: IntelligenceEvidence):
        github = evidence.github
        if not github:
            return "No GitHub data"
        reddit = evidence.reddit
        huggingface = evidence.huggingface

        repo = github.repository
        planning = github.planning
        discussions = github.discussions
        commits = github.commit_activity
        prs = github.pull_requests
        readme = github.readme

        parts = []
        parts.append(f"Project: {repo.full_name if repo else 'Unknown'}")
        parts.append(f"Description: {repo.description if repo else 'None'}")
        parts.append(
            f"Language: {repo.language if repo else 'Unknown'} | "
            f"Stars: {repo.stars if repo else 0} | "
            f"License: {repo.license if repo else 'Unknown'}"
        )
        parts.append("\n[Explicit Planning]")
        if planning:
            if planning.roadmap_text:
                parts.append(f"ROADMAP.md Summary:\n{planning.roadmap_text[:1500]}")
            else:
                parts.append("ROADMAP.md: None")
            if planning.milestones:
                ms_lines = []
                for m in planning.milestones:
                    title = m.get("title", "")
                    due = m.get("due_on", "No deadline")
                    prog = m.get("progress_percent", "?")
                    ms_lines.append(f"  - {title} (Due: {due}, Progress: {prog}%)")
                parts.append("Open Milestones:\n" + "\n".join(ms_lines))
            else:
                parts.append("Open Milestones: None")
            if planning.enhancement_issues:
                parts.append("Recent Enhancement/Proposal Issues:")
                for issue in planning.enhancement_issues:
                    parts.append(f"  - {issue}")
            else:
                parts.append("Recent Enhancement/Proposal Issues: None")
        else:
            parts.append("No planning data")
        parts.append("\n[Implicit Dynamics]")
        if commits:
            parts.append(
                f"30-day commits: {commits.commits_last_30_days}, "
                f"90-day commits: {commits.commits_last_90_days}"
            )
            parts.append(f"Active contributors: {commits.active_contributors_count}")
        else:
            parts.append("Commit activity data missing")
        if prs:
            recent_pr_titles = [pr.title for pr in prs[:5] if pr.title]
            if recent_pr_titles:
                parts.append("Recent PR Titles:")
                for t in recent_pr_titles:
                    parts.append(f"  - {t}")
            else:
                parts.append("No recent PR data")
        else:
            parts.append("PR data missing")
        parts.append("\n[Community Pulse]")
        if discussions and discussions.hot_topics:
            parts.append("Recent Hot Topics:")
            for topic in discussions.hot_topics:
                parts.append(f"  - {topic}")
        else:
            parts.append("Recent Hot Topics: None")
        parts.append("\n[Community Signals]")
        if reddit and reddit.posts:
            parts.append("Reddit Related Posts:")
            for post in reddit.posts[:5]:
                parts.append(f"  - {post}")
            parts.append(f"Reddit Mentions: {reddit.mentions}")
        else:
            parts.append("Reddit Related Posts: None")
        parts.append("\n[HuggingFace Signals]")
        if huggingface:
            parts.append(f"Downloads: {huggingface.downloads} | Likes: {huggingface.likes}")
            if huggingface.pipeline_tag:
                parts.append(f"Pipeline: {huggingface.pipeline_tag}")
            if huggingface.tags:
                parts.append("Tags: " + ", ".join(huggingface.tags[:10]))
            if huggingface.last_modified:
                parts.append(f"Last Modified: {huggingface.last_modified}")
        else:
            parts.append("HuggingFace Signals: None")
        if readme:
            parts.append(f"\n[README Summary]\n{readme[:1000]}")
        return "\n".join(parts)

    def predict(self, evidence: IntelligenceEvidence) -> RoadmapReport:
        evidence_text = self.format_roadmap_evidence(evidence)
        prompt = f"""
{ROADMAP_PROMPT}

Repository Evidence:

{evidence_text}
"""
        llm = deepseek_structured_model.with_structured_output(RoadmapReport)
        return llm.invoke(prompt)
