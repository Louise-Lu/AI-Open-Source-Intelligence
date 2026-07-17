from agent.github_agent import github_agent
from agent.trace import (
    clear_trace,
    get_trace
)

class ChatService:

    def chat(self, message: str):
        clear_trace()

        # 限制 Agent 递归深度，防止无限工具调用
        config = {"recursion_limit": 12}

        #============== 生产模式 invoke =====================
        # result = github_agent.invoke(
        #     {"messages": [("user", message)]},
        #     config=config
        # )

        # answer = result["messages"][-1].content
        # trace = get_trace()

        # return {
        #     "answer": answer,
        #     "trace": trace
        # }


       #=============== 开发模式 stream ==================
        final_answer = ""
        tool_calls_log = []

        print(f"\n{'='*40}")
        print(f"用户问题: {message}")
        print(f"{'='*40}")

        for event in github_agent.stream(
            {"messages": [("user", message)]},
            config=config,
            stream_mode="values"
        ):
            if "messages" not in event:
                continue

            latest_msg = event["messages"][-1]

            # ---------- 处理工具调用 ----------
            if hasattr(latest_msg, "type") and latest_msg.type == "tool":
                tool_name = getattr(latest_msg, "name", "unknown")
                raw_output = latest_msg.content

                # 根据工具名定制日志输出
                display_output = self._format_tool_output_for_log(tool_name, raw_output)

                print(f"\n🔧 调用工具: {tool_name}")
                print(f"   返回: {display_output}")
                tool_calls_log.append(f"{tool_name}: {display_output}")

            # ---------- 处理 AI 回答 ----------
            # if hasattr(latest_msg, "type") and latest_msg.type == "ai":
            #     if isinstance(latest_msg.content, str) and latest_msg.content.strip():
            #         final_answer = latest_msg.content
            #         print(f"\n🤖 最终回答:\n{final_answer[:500]}...")

        # 兜底
        # if not final_answer:
        #     result = github_agent.invoke(
        #         {"messages": [("user", message)]},
        #         config=config
        #     )
        #     final_answer = result["messages"][-1].content

        trace = get_trace()

        print(f"\n📊 Trace: {trace}")
        print(f"{'='*40}\n")

        return {
            "answer": final_answer,
            "trace": trace,
            "tool_calls": tool_calls_log
        }

    # ========== 新增：工具输出格式化方法 ==========
    @staticmethod
    def _format_tool_output_for_log(tool_name: str, output: str, max_len: int = 200) -> str:
        """根据不同工具，截断或清理日志输出，保留完整数据传给 LLM"""
        # 如果是字符串，先尝试解析为 JSON
        try:
            import json
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            data = output

        # 针对特定工具定制显示
        if tool_name in ("get_releases", "releases"):
            if isinstance(data, list):
                simplified = []
                for item in data:
                    simplified.append({
                        "tag_name": item.get("tag_name"),
                        "name": item.get("name"),
                        "published_at": item.get("published_at")
                    })
                return json.dumps(simplified, indent=2, ensure_ascii=False)
            elif isinstance(data, dict):
                return json.dumps({
                    "tag_name": data.get("tag_name"),
                    "name": data.get("name"),
                    "published_at": data.get("published_at")
                }, indent=2, ensure_ascii=False)

        # 默认：字符串过长则截断
        if isinstance(data, str) and len(data) > max_len:
            return data[:max_len] + f"... (截断，原长度 {len(data)})"
        elif isinstance(data, (dict, list)):
            text = json.dumps(data, indent=2, ensure_ascii=False)
            if len(text) > max_len:
                return text[:max_len] + "... (截断)"
            return text
        return str(data)
