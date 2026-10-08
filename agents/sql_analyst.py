import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.llm_pick import pick_llm
from models.schema import AgentState

def curate_question(state:AgentState)->AgentState:
    user_input = state.user_input
    llm = pick_llm("low")  # You can adjust the level based on your needs
    response = llm.chat([{"role": "user", "content": f"Curate the following user input into a clear and concise question: {user_input}"}])
    state.curated_ques = response
    return state

def prompt_query_context(state:AgentState)->AgentState:
    curated_ques = state.curated_ques

    