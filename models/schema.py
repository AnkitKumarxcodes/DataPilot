from operator import add
from typing import Annotated, Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """State passed between the data-agent steps."""

    message: Annotated[list[BaseMessage], add] = Field(
        default_factory=list,
        description="Messages exchanged during agent processing.",
    )
    user_input: str = Field(default="", description="Input provided by the user.")
    curated_ques: str = Field(default="", description="The clarified user question.")
    prompt_query_context: str = Field(
        default="", description="Prompt context used to generate a SQL query."
    )
    is_safe: Literal["Yes", "No"] = Field(
        default="No", description="Whether the requested query is safe to run."
    )
    generated_sql_query: str = Field(
        default="", description="SQL generated for the user's question."
    )
    sql_query_execution_result: str = Field(
        default="", description="Result of executing the generated SQL query."
    )
    comments: str = Field(
        default="", description="Comments explaining the safety judgment."
    )
    final_ans: str = Field(default="", description="Final response to the user.")


class judgeSchema(BaseModel):
    """Model for judging the safety of a SQL query."""

    is_safe: Literal["Yes", "No"] = Field(
        default="No", description="Whether the SQL query is safe to run."
    )
    sql_query: str = Field(
        default="", description="The SQL query, or an empty string if unsafe."
    )
    comments: str = Field(
        default="", description="Comments explaining the safety judgment."
    )

class ETLAgentSchema(BaseModel):
    message: Annotated[list[BaseMessage], add] = Field(
            default_factory=list,
            description="Messages exchanged during agent processing.",
        )

class RouterSchema(BaseModel):
    answer: Literal["sql", "etl"] = Field(... , description = "Indicates whether the user's question is related to SQL or ETL operations")
    comments: str = Field(... , description = "Additional comments or feedbacks regarding classication of query")

class DataAgentSchema(BaseModel):
    message: Annotated[list[BaseMessage], add] = Field(
                default_factory=list,
                description="Messages exchanged during agent processing.",
            )
    route_response : str = Field(... , description="The response from the router indicating where ETl operation or SQl query should be carried out")