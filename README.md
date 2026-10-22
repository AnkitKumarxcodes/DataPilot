# DataPilot

**Ask your database questions in plain English.** DataPilot is a LangGraph-based data agent that turns natural-language questions into SQL, checks the SQL for safety, runs it against **PostgreSQL or MySQL**, and explains the result in plain language. A second agent handles simple ETL tasks (pull data from an API, transform it with pandas), and a top-level router decides which agent should take a request.

> **Status: early / work in progress.** The SQL agent and the database layer work end to end. There is no CLI yet, and a few safety and wiring issues are still open. See [Known limitations](#known-limitations) before pointing it at a database you care about.

---

## Contents

- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Usage](#usage)
- [Database support](#database-support)
- [Sample dataset](#sample-dataset)
- [Configuration](#configuration)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## How it works

DataPilot is built as three LangGraph graphs: a router on top, and two specialist agents below it.

### 1. Top-level router

![Top-level data agent graph](data_agent.png)

The `router_node` asks an LLM (structured output) whether the user's request is a **SQL** question or an **ETL** task, then hands it to `sql_node` or `etl_node`.

### 2. SQL analyst agent

![SQL agent graph](sql_agent_graph.png)

| Step | What it does |
|---|---|
| `curate_question` | Rewrites the raw input into a clear, concise question. |
| `prompt_query_context` | Reflects the live database schema (tables, columns, primary and foreign keys, a few sample rows) and builds a dialect-aware prompt for PostgreSQL or MySQL. |
| `generate_sql_query` | Generates exactly one read-only `SELECT` (or `WITH ... SELECT`), returned as JSON. |
| `isSafe` | A second LLM pass acts as a safety judge and rejects anything that modifies data or structure. |
| `execute_query` / `cancelled_query` | Approved queries run; rejected ones short-circuit with an explanation. |
| `represent_final_ans` | Turns raw rows into a short, readable answer. |

### 3. ETL agent

![ETL agent graph](etl_analyst_graph.png)

A ReAct-style loop: `llm_node` decides which tool to call, `tool_node` runs it, and the result feeds back until the model has nothing left to call. Tools:

- `extract_load_tool`: fetch JSON from an API endpoint and save it as CSV, JSON, or Parquet.
- `transform_load_tool`: look at the first rows of a file, have the LLM write pandas code for the requested transformation, and run it.

---

## Project structure

```
datapilot/
├── agents/
│   ├── dataagent.py          # top-level router graph (SQL vs ETL)
│   ├── sql_analyst.py        # node functions for the SQL agent
│   ├── sql_agent_graph.py    # compiled SQL agent graph
│   └── etl_analyst.py        # ReAct-style ETL agent + tools
├── models/
│   └── schema.py             # Pydantic state/output models (AgentState, RouterSchema, ...)
├── utils/
│   ├── database.py           # SQLAlchemy engine, schema reflection, SQL execution
│   ├── etl_tools.py          # extract / transform helpers used by the ETL agent
│   └── llm_pick.py           # picks an LLM by capability level (low / medium / high)
├── data/                     # sample ride-sharing CSVs (users, vehicles, rides, payments, ratings)
├── feed_db.py                # creates tables and seeds the sample data
├── pyproject.toml
└── README.md
```

---

## Quick start

### Requirements

- Python **3.12+**
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- A running **PostgreSQL** or **MySQL** server with an empty database created for DataPilot
- API keys for the LLM providers below (all have free tiers)

### Install

```bash
git clone https://github.com/AnkitKumarxcodes/DataPilot.git
cd DataPilot
uv sync
```

### Configure

Create a `.env` file in the project root:

```env
# Database
DB_DIALECT=postgresql        # or: mysql
DB_HOST=localhost
DB_PORT=5432                 # 3306 for MySQL
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=datapilot

# LLM providers
GOOGLE_API_KEY=...
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
```

`.env` is git-ignored. Never commit real credentials.

### Seed the sample data

Create the database first (for example `CREATE DATABASE datapilot;`), then:

```bash
uv run python feed_db.py
```

This creates five tables and loads the CSVs in batches. It does **not** clear existing rows, so run it once on an empty database. Expected output:

```
Connected to postgresql database.
Loaded users.csv (10,000 rows)
Loaded vehicles.csv (3,000 rows)
Loaded rides.csv (20,000 rows)
Loaded payments.csv (16,073 rows)
Loaded ratings.csv (12,000 rows)
```

---

## Usage

There is no CLI yet (it's on the [roadmap](#roadmap)), so for now you call the SQL agent from Python. Run this from the project root:

```python
from agents.sql_agent_graph import sql_analyst

result = sql_analyst.invoke({"user_input": "Which 3 cities have the most completed rides?"})

print(result["generated_sql_query"])
print(result["final_ans"])
```

Example questions that work against the sample dataset:

- "What is the average fare for completed rides?"
- "Which drivers have the highest average rating?"
- "How many rides were cancelled by the driver, grouped by reason?"
- "Show monthly ride counts for 2025."

The agent adapts its SQL to the configured dialect, so the same question produces `date_trunc(...)` on PostgreSQL and `DATE_FORMAT(...)` on MySQL.

---

## Database support

| Database | Driver | Seeding | Schema reflection | Query execution |
|---|---|---|---|---|
| PostgreSQL | `psycopg2` | ✅ | ✅ | ✅ |
| MySQL / MariaDB | `PyMySQL` | ✅ | ✅ | ✅ |

Verified against PostgreSQL 16 and MariaDB 10.11: identical seed results, and joins, CTEs, window functions, `LIKE`, and dialect-specific date functions all execute correctly through `DatabaseUtil` on both.

`DatabaseUtil` (in `utils/database.py`) is the single place that owns the SQLAlchemy engine. It also exposes `schema_details(schema_name, sample_rows=5)`; pass `sample_rows=0` if sample values must not be sent to an LLM provider.

---

## Sample dataset

A synthetic ride-sharing dataset in `data/`:

| Table | Rows | Description |
|---|---|---|
| `users` | 10,000 | Riders and drivers |
| `vehicles` | 3,000 | Driver vehicles |
| `rides` | 20,000 | Requests, pickups, dropoffs, fares, status |
| `payments` | 16,073 | Payment method, status, transaction ids |
| `ratings` | 12,000 | 1–5 ratings with comments |

---

## Configuration

| Variable | Required | Description |
|---|---|---|
| `DB_DIALECT` | no | `postgresql` (default) or `mysql` |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | yes | Database connection settings |
| `GOOGLE_API_KEY` | yes | Used for the `low` model (question curation, answer formatting) |
| `GROQ_API_KEY` | yes | Used for the `medium` model (SQL generation, safety judge, ETL) |
| `OPENROUTER_API_KEY` | yes | Used for the `high` model (router) |

Models are chosen in `utils/llm_pick.py` by capability level, so swapping providers is a one-file change.

---

## Known limitations

Being upfront about where this stands:

- **No database-level read-only enforcement.** Safety currently relies on the LLM judge. Writes are rolled back only because nothing calls `commit()`, and on MySQL a `DROP TABLE` would commit implicitly. Next priority: open connections in read-only mode.
- **ETL agent runs LLM-generated code with `exec()`.** Treat it as unsafe; do not expose it to untrusted input.
- **Router wiring is unfinished.** `agents/dataagent.py` imports its sibling agents with paths that only resolve when run from inside `agents/`, `route_response` has no default on its state model, and `sql_node` appends the raw result dict to the message list. Use the SQL agent directly for now.
- **`etl_analyst.py` renders its graph PNG at import time**, which needs network access. It should move behind a `__main__` guard.
- **No tests in the repository yet.**
- **No retry on SQL errors.** If the generated query fails, the error is not fed back to the model.
- **Three separate LLM providers** are required, which makes setup heavier than it should be.

---

## Roadmap

- [ ] Enforce read-only sessions on both PostgreSQL and MySQL
- [ ] Fix router wiring; move import-time side effects behind `__main__`
- [ ] Test suite with PostgreSQL and MySQL service containers in CI
- [ ] Self-correcting SQL (retry with the database error)
- [ ] Installable CLI: `datapilot connect`, `datapilot ask`, `datapilot chat`
- [ ] Single configurable model setting (including local models via Ollama)
- [ ] SQLite support
- [ ] Sandboxed ETL execution

---

## Tech stack

Python · LangGraph · LangChain · SQLAlchemy · Pydantic · pandas · PostgreSQL · MySQL · Gemini / Groq / OpenRouter

---

## Author

**Ankit Kumar**: [GitHub](https://github.com/AnkitKumarxcodes) · [Portfolio](https://myportfolio-orpin-tau.vercel.app)
