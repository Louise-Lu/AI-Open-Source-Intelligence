EXTRACTOR_PROMPT = """
从用户问题中提取技术相关实体。

实体包括：

- 开源项目
- AI模型
- 公司
- 产品
- 框架
- 工具


规则：

1. 用户提到任何具体名称，都必须返回。
2. 不判断任务类型。
3. 不猜测 github owner/repo。
4. 不猜测 HuggingFace model id。
输出 JSON:

{
 "entities":[
   {
    "name":"xxx"
   }
 ]
}


用户问题:
{query}
"""
