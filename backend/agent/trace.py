from contextvars import ContextVar


tool_trace = ContextVar(
    "tool_trace",
    default=[]
)


def add_trace(
    tool_name: str,
    tool_input: dict,
    tool_output: dict
):

    trace = tool_trace.get()

    trace.append(
        {
            "tool": tool_name,
            "input": tool_input,
            "output": tool_output,
        }
    )

    tool_trace.set(trace)



def get_trace():

    return tool_trace.get()



def clear_trace():

    tool_trace.set([])