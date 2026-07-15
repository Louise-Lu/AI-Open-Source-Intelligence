from pydantic import BaseModel, Field
## 仓情报报告 - markdown 

class AnalysisResponse(BaseModel):
    """Repository Analysis 输出"""

    analysis: str = Field(
        description="Markdown 格式的 GitHub Repository Intelligence Report"
    )
