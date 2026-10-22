import os
from collections.abc import Mapping
from dataclasses import dataclass
from types import TracebackType

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, inspect, select, text
from sqlalchemy.engine import Engine, URL, create_engine
from sqlalchemy.exc import SQLAlchemyError


_DRIVERS = {
    "postgresql": "postgresql+psycopg2",
    "mysql": "mysql+pymysql",
}


@dataclass(frozen=True)
class DatabaseConfig:
    """Connection settings for a supported database dialect."""

    dialect: str
    host: str | None
    port: int | None
    username: str | None
    password: str | None
    database: str | None

    @property
    def url(self) -> URL:
        """Build a URL without requiring password string escaping."""
        return URL.create(
            drivername=_DRIVERS[self.dialect],
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )


def load_db_config_from_env(
    environ: Mapping[str, str] | None = None,
) -> DatabaseConfig:
    """Load and validate database settings from environment variables."""
    if environ is None:
        load_dotenv()
        values = os.environ
    else:
        values = environ
    dialect = values.get("DB_DIALECT", "postgresql").strip().lower()
    supported = ", ".join(_DRIVERS)
    if dialect not in _DRIVERS:
        raise ValueError(
            f"Unsupported DB_DIALECT {dialect!r}; supported dialects: {supported}."
        )

    port_value = values.get("DB_PORT")
    try:
        port = int(port_value) if port_value else None
    except ValueError as exc:
        raise ValueError("DB_PORT must be an integer.") from exc

    return DatabaseConfig(
        dialect=dialect,
        host=values.get("DB_HOST") or None,
        port=port,
        username=values.get("DB_USER") or None,
        password=values.get("DB_PASSWORD") or None,
        database=values.get("DB_NAME") or None,
    )


class DatabaseUtil:
    """Inspect database schemas and optionally include a few sample rows."""

    def __init__(
        self,
        db_config: DatabaseConfig | None = None,
        *,
        engine: Engine | None = None,
        url: URL | str | None = None,
    ) -> None:
        if engine is not None and (db_config is not None or url is not None):
            raise ValueError("Pass an engine, a URL, or a config, not more than one.")
        if url is not None and db_config is not None:
            raise ValueError("Pass a URL or a config, not both.")

        if engine is not None:
            self.engine = engine
        else:
            connection_url = url or (db_config or load_db_config_from_env()).url
            self.engine = create_engine(connection_url, pool_pre_ping=True)

    @property
    def dialect(self) -> str:
        """Return the SQLAlchemy dialect name for this engine."""
        return self.engine.dialect.name

    def schema_details(
        self,
        schema_name: str | None = None,
        sample_rows: int = 5,
    ) -> str:
        """Return table, column, key, and optionally sample-row details."""
        if sample_rows < 0:
            raise ValueError("sample_rows must be zero or greater.")

        try:
            inspector = inspect(self.engine)
            if schema_name is None:
                schema_name = inspector.default_schema_name

            details = [f"Database Schema: {schema_name}\n"]
            table_names = inspector.get_table_names(schema=schema_name)

            with self.engine.connect() as connection:
                for table_name in table_names:
                    details.append(f"Table: {table_name}\n")
                    columns = inspector.get_columns(table_name, schema=schema_name)
                    for column in columns:
                        details.append(
                            f"  Column: {column['name']}, Type: {column['type']}\n"
                        )

                    primary_key = inspector.get_pk_constraint(
                        table_name, schema=schema_name
                    ).get("constrained_columns") or []
                    if primary_key:
                        details.append(f"  Primary Key: {', '.join(primary_key)}\n")

                    foreign_keys = inspector.get_foreign_keys(
                        table_name, schema=schema_name
                    )
                    for foreign_key in foreign_keys:
                        referred_table = foreign_key.get("referred_table")
                        local_columns = foreign_key.get("constrained_columns") or []
                        referred_columns = foreign_key.get("referred_columns") or []
                        for local_column, referred_column in zip(
                            local_columns, referred_columns
                        ):
                            details.append(
                                f"  Foreign Key: {local_column} -> "
                                f"{referred_table}.{referred_column}\n"
                            )

                    if sample_rows:
                        details.append("  Sample Data:\n")
                        reflected_table = Table(
                            table_name,
                            MetaData(),
                            schema=schema_name,
                            autoload_with=connection,
                        )
                        rows = connection.execute(
                            select(reflected_table).limit(sample_rows)
                        )
                        for row in rows:
                            values = tuple(
                                self._truncate(str(value)) for value in row
                            )
                            details.append(f"    {values}\n")

            return "".join(details)
        except SQLAlchemyError as exc:
            return f"Error retrieving schema details: {exc}\n"

    def execute_sql(self, sql_query: str) -> str:
        """Execute SQL with the configured MySQL or PostgreSQL engine."""
        if not sql_query.strip():
            raise ValueError("SQL query must not be empty.")

        with self.engine.connect() as connection:
            result = connection.execute(text(sql_query))
            if not result.returns_rows:
                return f"Query executed successfully ({result.rowcount} rows affected)."

            rows = [tuple(row) for row in result.fetchall()]
            return str(rows)

    @staticmethod
    def _truncate(value: str, max_length: int = 50) -> str:
        """Limit a sample value's rendered length."""
        if len(value) <= max_length:
            return value
        return f"{value[: max_length - 3]}..."

    def dispose(self) -> None:
        """Dispose of the engine's connection pool."""
        self.engine.dispose()

    def __enter__(self) -> "DatabaseUtil":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.dispose()
