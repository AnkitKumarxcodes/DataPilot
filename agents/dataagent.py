import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__) , '..')))


from models.schema import RouterSchema , DataAgentSchema

from utils.etl_tools import ETLAgentTools
from utils.llm_pick import pick_llm
from langchain_core.messages import AIMessage , HumanMessage,SystemMessage,ToolMessage
from langgraph.graph import StateGraph , START , END
from langchain.tools import tool
from etl_analyst import etl_analyst 
from sql_agent_graph import sql_analyst

llm = pick_llm("high")

llm_router = llm.with_structured_output(RouterSchema)

def router_node(state:DataAgentSchema):
    message = state.message[-1].content

    route_response_dict = llm_router.invoke(message).model_dump()
    route_response = route_response_dict['answer']
    state.route_response = route_response
    return state

def etl_node(state:DataAgentSchema):
    message = state.message[-1].content

    etl_tools = ETLAgentTools()
    response = etl_analyst.invoke(
    {"message": [HumanMessage(content = f"""
        {message}
    """)]}
    )
    state.message = state.message + [response]

    return state

def sql_node(state:DataAgentSchema):
    message = state.message[-1].content
    input_schema = {
        "message": [],
        "user_input": f"{message}",
        "curated_ques": "",
        "prompt_query_context": "",
        "is_safe": "No",
        "generated_sql_query": "",
        "sql_query_execution_result": "",
        "comments": "",
        "final_ans": "",
    }

    response =sql_analyst.invoke(input_schema)

    state.message = state.message + [response]

    return state

data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")

def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")


data_agent_graph.add_conditional_edges("router_node", route_edge,
                                      {
                                          "sql_node": "sql_node",
                                          "etl_node": "etl_node"
                                      })

data_agent = data_agent_graph.compile()

# from IPython.display import display , Image
# img = Image(data_agent.get_graph().draw_mermaid_png())

# with open("data_agent.png" , "wb") as f:
#     f.write(img.data)




