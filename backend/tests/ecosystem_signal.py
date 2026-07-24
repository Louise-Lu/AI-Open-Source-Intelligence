import os
from dotenv import load_dotenv

load_dotenv()
def test_real_repo():
    from backend.sources.github import EcosystemSignalTool, GitHubClient

    token = os.getenv("GITHUB_TOKEN")
    client = GitHubClient(token=token)

    competitor_map = {"crewAIInc/crewAI": ["AutoGPT", "MetaGPT"]}
    tool = EcosystemSignalTool(client=client, competitor_map=competitor_map)

    # 手动调用一次 API 并打印状态码，确认 SBOM 请求是否成功
    print("\n手动测试 SBOM 请求...")
    sbom_resp = client.get(
        "/repos/crewAIInc/crewAI/dependency-graph/sbom",
        headers={"Accept": "application/vnd.github.spdx+json"},
    )
    print("SBOM 状态码:", sbom_resp.status_code)
    if sbom_resp.status_code == 200:
        data = sbom_resp.json()
        print("SBOM 顶层 keys:", list(data.keys()))
        rels = data.get("relationships", [])
        print("relationships 条目数:", len(rels))
        if rels:
            print("前3条 relationships:", rels[:3])
    else:
        print("SBOM 请求失败，响应内容:", sbom_resp.text[:200])

    print("\n调用 tool.get_ecosystem_signals...")
    
    result = tool.get_ecosystem_signals("crewAIInc", "crewAI")
    print(f"总依赖数: {len(result['dependencies'])}")
    print(f"前 20 个依赖: {result['dependencies'][:20]}")
    print(f"下游项目数: {result['dependents_count']}")
    print(f"Awesome 收录: {result['awesome_list_mentions']}")
    print(f"竞品: {result['competitors']}")

    
if __name__ == "__main__":
    print("测试开始...")
    test_real_repo()
    print("测试通过！")