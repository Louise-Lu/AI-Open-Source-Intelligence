from pydantic import BaseModel, Field


class RepositoryComparisonReport(BaseModel):
    """两个 Repository 的分析报告（Markdown）"""

    comparison: str = Field(
        description="Markdown 格式的 Repository Comparison Report"
    )