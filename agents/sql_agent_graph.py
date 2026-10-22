from langgraph.graph import END, StateGraph
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.schema import AgentState

from agents.sql_analyst import (
    cancelled_query,
    curate_question,
    execute_query,
    generate_sql_query,
    isSafe,
    prompt_query_context,
    represent_final_ans,
)

sql_agent_graph = StateGraph(AgentState)

sql_agent_graph.add_node("curate_question", curate_question)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql_query", generate_sql_query)
sql_agent_graph.add_node("isSafe", isSafe)
sql_agent_graph.add_node("cancelled_query", cancelled_query)
sql_agent_graph.add_node("execute_query", execute_query)
sql_agent_graph.add_node("represent_final_ans", represent_final_ans)


def route_after_safety_check(state: AgentState) -> str:
    """Send approved queries to execution and rejected queries to cancellation."""
    if state.is_safe == "Yes" and state.generated_sql_query.strip():
        return "execute_query"
    return "cancelled_query"


sql_agent_graph.set_entry_point("curate_question")
sql_agent_graph.add_edge("curate_question", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql_query")
sql_agent_graph.add_edge("generate_sql_query", "isSafe")
sql_agent_graph.add_conditional_edges(
    "isSafe",
    route_after_safety_check,
    {
        "execute_query": "execute_query",
        "cancelled_query": "cancelled_query",
    },
)
sql_agent_graph.add_edge("execute_query", "represent_final_ans")
sql_agent_graph.add_edge("cancelled_query", "represent_final_ans")
sql_agent_graph.add_edge("represent_final_ans", END)

sql_analyst = sql_agent_graph.compile()

# import IPython
# if __name__ == "__main__":

#     from IPython.display import Image, display

#     img = Image(compiled_sql_agent_graph.get_graph().draw_mermaid_png())
#     with open("sql_agent_graph.png" , "wb") as f:
#         f.write(img.data)

#     input_schema = {
#         "message": [],
#         "user_input": "What is the maximum transaction amount",
#         "curated_ques": "",
#         "prompt_query_context": "",
#         "is_safe": "No",
#         "generated_sql_query": "",
#         "sql_query_execution_result": "",
#         "comments": "",
#         "final_ans": "",
#     }

#     result = compiled_sql_agent_graph.invoke(input_schema)
#     print(result["is_safe"])
