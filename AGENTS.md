# Project Instructions

## Purpose

This is a learning project based on a guided YouTube tutorial for building
an end-to-end Data Agent.

I am implementing the project myself and using Codex as a tutor, reviewer,
debugger, and software-engineering guide.

## Important Learning Rule

Do NOT automatically implement entire features for me.

Prefer helping me understand the concepts, architecture, and code first.

When I ask for help:
1. Explain what the existing code is doing.
2. Explain why the design/approach is being used.
3. Point out problems or improvements.
4. Only write or modify code when I explicitly ask you to.

If I provide code from the tutorial, help me understand and improve it rather
than replacing it with a completely different implementation.

## Development Principles

- Prefer simple, maintainable Python.
- Use type hints where appropriate.
- Follow a modular project structure.
- Keep business logic separate from API/routes and database access.
- Use Pydantic for data validation where appropriate.
- Write tests for important functionality.
- Use Git properly and avoid unnecessary changes.
- Do not introduce dependencies without explaining why they are needed.
- Prefer understanding standard Python/software-engineering solutions before
  adding a framework abstraction.

## Learning Goals

I specifically want to improve my understanding of:

- Python software development
- APIs and FastAPI
- PostgreSQL and database design
- Pydantic
- Git and version control
- testing and debugging
- LLM APIs
- tool calling
- LangChain
- LangGraph
- agents and ReAct
- multi-agent orchestration
- evaluation
- production AI architecture

## Interaction Style

Be concise and practical.

When explaining code, explain the underlying software-engineering concept,
not just what each line does.

If my implementation is incorrect, tell me directly and explain why.

Do not over-engineer the project just to make it look more advanced.

When there are multiple reasonable approaches, explain the tradeoff briefly
and let me choose.

## Safety Before Changes

Before making substantial changes:
- inspect the existing code;
- explain what you intend to change;
- avoid unrelated refactoring;
- preserve working code unless the change requires otherwise.

Do not make large changes across the repository unless I explicitly request it.

## Current Project State

- This remains a learning project for an end-to-end Data Agent; keep changes
  incremental and explain concepts before expanding features.
- Database configuration is loaded by `load_db_config_from_env()` in
  `utils/database.py`. It supports `DB_DIALECT` (`postgresql` by default, or
  `mysql`) and `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`.
  URLs use SQLAlchemy `URL.create()` with an allowlisted driver. Never record
  credential values here; generic names such as `USERNAME` collide with
  Windows environment variables.
- `models/schema.py` defines a Pydantic `AgentState` with usable defaults and a
  list reducer for messages. `user_input` is a plain string field.
- `utils/database.py` owns a SQLAlchemy engine, supports PostgreSQL through
  psycopg2 and MySQL through PyMySQL, and uses SQLAlchemy inspection for table,
  column, primary-key, and foreign-key details. It can include up to five sample
  rows by default; values are stringified and truncated to 50 characters.
  `sample_rows=0` disables sampling. Sample rows may contain personal data and
  are included in the LLM prompt by the current SQL analyst flow, so use the
  zero-sample option when that data should not leave the database environment.
  Dispose the engine with `dispose()` or the context manager.
- `agents/sql_analyst.py` chooses `public` for PostgreSQL and the default schema
  for MySQL, then includes the connected database dialect in its SQL prompt.
  It generates SQL but does not execute it. `feed_db.py` creates the same
  PostgreSQL or MySQL tables with SQLAlchemy Core and loads CSV data in batches.
  The destination database must already exist, and the seeder does not clear
  existing rows before loading.
- `.env.example` documents database, LLM, and Ollama settings. `.env` is ignored
  by Git; never put real credentials in the example file or source code.
- Dependencies: SQLAlchemy 2.x provides engine/URL/reflection support;
  PyMySQL is the pure-Python MySQL driver; psycopg2-binary remains the
  PostgreSQL driver; pytest is a development dependency.
- `uv run pytest` passed all seven tests, including SQLite schema/configuration
  checks and a CSV seeding test. The actual five CSV files also loaded into an
  in-memory SQLite database. No live MySQL or PostgreSQL seeding run has been
  done. Existing work is uncommitted; inspect `git status` before further edits.
- Next: continue the current Data Agent phase; query validation and execution
  remain out of scope.
