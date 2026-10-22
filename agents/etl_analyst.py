import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__) , '..')))


from models.schema import ETLAgentSchema

from utils.etl_tools import ETLAgentTools
from utils.llm_pick import pick_llm
from langchain_core.messages import AIMessage , HumanMessage,SystemMessage,ToolMessage
from langgraph.graph import StateGraph , START , END
from langchain.tools import tool

@tool
def extract_load_tool(url:str , output_folder:str , format:str):
    """
    this tool extracts datafrom the API (url) and loads into the desired into destination

    Args:
        url(str):the API endpoint from whcich to extract data.
        Output_folder(str):The folder where the extracted data will be saved

    Returns:
        str:A message indicating the success or failure of the operation
    """

    etl_tools = ETLAgentTools()

    return etl_tools.extract_and_load(url , output_folder , format)

@tool
def transform_load_tool(input_file_path:str , output_folder:str , output_format:str , user_question:str)->str:
    """
       
    This tool transforms the data from the specified file and loads it into the desired location(output folder).

    Args:
        input_file_path(Str):the path to the file the containing the data to be transormed 
        output_folder(Str);the folder where the transformed data will be saved 
        format(str);the format of the data(csv , parquet , json)
    Returns:
        str: A message indicating success or failure of operation
    
    """
    etl_tools = ETLAgentTools()
    top_3_rows = etl_tools.transform_load_context(input_file_path)
    llm = pick_llm("medium")

    prompt = f"""
        You are an ETL agent, you have been provided with the top 3 rows of a dataset. You need to provide only the pandas code that will help to perform the right ETL operation as per the user's question.Do not provide any explaination or comments , only the python code.The code should be in a format that can be executed in a python environment with pandas installed.\n

        Create pandas Dataframe from the data stored in the file : {input_file_path} and then write the code to transform and save the data at {output_folder}.
        here is the user's question: {user_question}\n
        here are the top 3 rows for context : {top_3_rows}\n

    """

    response = llm.invoke(prompt).content
    code = response.strip().strip('```').strip().lstrip('python').strip()
    results = etl_tools.execute_python(code)
    return f"The data is transformed and saved at {output_folder} in {output_format}.\n\n Pandas Code executed:\n {code}\n\n Execution Result:\n {results}"

tools = [extract_load_tool , transform_load_tool]

llm = pick_llm("medium")
llm_bind = llm.bind_tools(tools)


#---------------------AgentGraph-----------------------------------------#

def llm_node(state:ETLAgentSchema):
    message = state.message
    system_message = SystemMessage(
        content=(
            "You are an ETL assistant. Use the available tools to perform "
            "the requested extraction or transformation. Ask for missing "
            "required details."
        )
    )

    response = llm_bind.invoke([system_message, *state.message])
    state.message = state.message + [response]
    return state

def tool_node(state:ETLAgentSchema):
    """
    This is responsible for invoking the appropriate tool based on the user's question only
    """
    tool_calls = state.message[-1].tool_calls
    tools_results = []
    tools_by_name = {tool.name: tool for tool in tools}

    for tool_call in tool_calls:
        tool = tools_by_name[tool_call['name']]
        observation = tool.invoke(tool_call['args'])
        tools_results.append(ToolMessage(content = observation , tool_call_id = tool_call['id']))

    state.message = state.message + tools_results
    return state

#--------------------------Nodes and Edges----------------------------

etl_analyst_graph = StateGraph(ETLAgentSchema)
etl_analyst_graph.add_node("llm_node" , llm_node)
etl_analyst_graph.add_node("tool_node"  , tool_node)

etl_analyst_graph.add_edge(START , "llm_node")

def is_tool_call(state:ETLAgentSchema):
    tool_calls = state.message[-1].tool_calls

    if tool_calls:
        return "tool_node"
    else:
        return "end"

etl_analyst_graph.add_conditional_edges(
    "llm_node" , is_tool_call,
    {
        "tool_node":"tool_node",
        "end" : END
    }
)

etl_analyst_graph.add_edge("tool_node" , "llm_node")

etl_analyst = etl_analyst_graph.compile()

from IPython.display import display , Image

img = Image(etl_analyst.get_graph().draw_mermaid_png())
with open("etl_analyst_graph.png" , "wb") as f:
    f.write(img.data)

# response = etl_analyst.invoke(
#     {"message": [HumanMessage(content = "I want to extract data from the API endpoint 'https://pokeapi.co/api/v2/pokemon/'.i want to save it to data\\extract folder , in csv format , then remove name column and save in data\\extract")]}
# )

# print(response)


    