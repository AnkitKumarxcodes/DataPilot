
import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from models.schema import judgeSchema
from utils.llm_pick import pick_llm

llm = pick_llm("medium")

llm_judge = llm.with_structured_output(
    judgeSchema,
    method="function_calling"
)

sql_query = "SELECT name, age FROM users WHERE age === 25;"

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

print(type(response))
