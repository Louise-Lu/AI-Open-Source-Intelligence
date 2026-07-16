from agent.github_agent import github_agent
from agent.trace import (
    clear_trace,
    get_trace
)

class ChatService:

    def chat(self, message:str):

        clear_trace()


        result = github_agent.invoke(
            {
                "messages":[
                    (
                        "user",
                        message
                    )
                ]
            }
        )


        answer = result["messages"][-1].content


        trace = get_trace()


        return {
            "answer": answer,
            "trace": trace
        }
    

