import json
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.schema import AgentState ,judgeSchema
from utils.database import DatabaseUtil, load_db_config_from_env
from utils.llm_pick import pick_llm


def curate_question(state: AgentState) -> AgentState:
    llm = pick_llm("low")
    response = llm.invoke(
        "Curate the following user input into a clear and concise question: "
        f"{state.user_input}"
    )
    state.curated_ques = response.content
    state.message += [HumanMessage(content=state.curated_ques)]
    return state


def prompt_query_context(state: AgentState) -> AgentState:
    with DatabaseUtil(load_db_config_from_env()) as db_obj:
        dialect = db_obj.dialect
        schema_name = "public" if dialect == "postgresql" else None
        schema_info = db_obj.schema_details(schema_name)
    dialect_label = "PostgreSQL" if dialect == "postgresql" else "MySQL"

    prompt = f"""
You are an AI SQL analyst. Translate a user's natural-language question into one
read-only SQL query that answers it.

Original user question:
{state.user_input}

Clarified question:
{state.curated_ques}

Schema and table definitions:
{schema_info}

Instructions:
1. Use the clarified question to understand the user's intent. If it conflicts
   with the original question or remains ambiguous, do not guess.
2. Target database dialect: {dialect_label}.
   - For PostgreSQL, use PostgreSQL-compatible syntax.
   - For MySQL, use MySQL-compatible syntax.
   Do not mix dialect-specific syntax.
3. Use only tables, columns, and relationships present in the supplied schema.
4. Generate exactly one read-only SELECT query (a read-only WITH ... SELECT is
   allowed). Never generate a statement that modifies data or database structure.
5. Check that tables, columns, joins, filters, and syntax are valid for the schema.
6. Do not claim the query has been executed or tested.
7. Limit results to 10 rows unless the user specified another limit.
8. Set is_safe to "No" and sql_query to an empty string if the request requires
   data modification, cannot be answered from the schema, or is too ambiguous.

Return only valid JSON with exactly these keys:
{{
  "is_safe": "Yes or No",
  "sql_query": "The SQL query, or an empty string if no safe query can be produced"
}}
"""
    state.prompt_query_context = prompt

    return state

def generate_sql_query(state: AgentState) -> AgentState:
    """Generate a SQL query based on the curated question and schema context."""
    llm = pick_llm("medium")
    response = llm.invoke(state.prompt_query_context)
    try:
        generated = json.loads(response.content)
        state.generated_sql_query = generated["sql_query"]
        state.is_safe = generated.get("is_safe", "No")
    except (json.JSONDecodeError, TypeError, KeyError):
        state.generated_sql_query = ""
        state.is_safe = "No"
    return state

def isSafe(state: AgentState) -> AgentState:
    """Determine if the generated SQL query is safe to execute."""

    sql_query = state.generated_sql_query

    llm = pick_llm("medium")

    llm_judge = llm.with_structured_output(judgeSchema)

    # sql_query = "SELECT * FROM users WHERE user_id = 1;"

    prompt = f"""
        You are an AI SQL safety analyst.

        Evaluate the supplied SQL query for read-only safety
        on MySQL or PostgreSQL.

        Rules:
        1. Only read-only data retrieval queries are permitted.
        2. Reject INSERT, UPDATE, DELETE, DROP, ALTER, and other
        statements that modify data or database structure.
        3. Do not execute the query.
        4. Preserve the original query; do not rewrite it.
        5. If the query is unsafe or cannot be evaluated reliably,
        set is_safe to "No" and sql_query to an empty string.
        6. If the query is safe, return the original query.
        7. Explain any SQL correctness issues in comments.
        8. Follow the provided output schema.

        SQL query to evaluate:
        {sql_query}
        """

    response = llm_judge.invoke(prompt)

    state.is_safe = response.is_safe
    state.generated_sql_query = response.sql_query
    state.comments = response.comments
    return state


def cancelled_query(state: AgentState) -> AgentState:
    """Handle the case where the SQL query is deemed unsafe."""
    comments = state.comments
    state.final_ans = (
        f"The generated SQL query is not safe to execute. Reason: {comments}. "
        "Please revise your question or provide more context."
    )

    return state

def execute_query(state: AgentState) -> AgentState:
    """Execute the generated SQL query and store the result."""

    if state.is_safe != "Yes" or not state.generated_sql_query.strip():
        state.sql_query_execution_result = "Query was not executed because it was not approved as safe."
        return state

    sql_query = state.generated_sql_query
    conn_details = load_db_config_from_env()
    with DatabaseUtil(conn_details) as obj:
        execution_result = obj.execute_sql(sql_query)
    state.sql_query_execution_result = execution_result

    return state

def represent_final_ans(state: AgentState) -> AgentState:
    """Format the final answer to be returned to the user."""
    execution_result = state.sql_query_execution_result
    curated_question = state.curated_ques
    llm = pick_llm("low")

    prompt = f"""
        You are an AI assistant that formats SQL query results for user readability.
        The final  answer should be concise, clear, and informative.The final answer should be in a human-readable format, summarizing the query results and providing any relevant insights.
        The SQL query result is:
        {execution_result}
        here is the user's original question:
        {curated_question} 
        """

    response = llm.invoke(prompt).content

    state.final_answer = response

    return state