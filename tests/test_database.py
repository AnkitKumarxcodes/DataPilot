from collections.abc import Iterator

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine
from sqlalchemy.engine import Engine, make_url

from utils.database import DatabaseUtil, load_db_config_from_env


@pytest.fixture
def sqlite_engine() -> Iterator[Engine]:
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    users = Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100), nullable=False),
    )
    rides = Table(
        "rides",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("users.id")),
        Column("note", String(200)),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(users.insert(), [{"id": 1, "name": "Rider"}])
        connection.execute(
            rides.insert(),
            [{"id": 10, "user_id": 1, "note": "sample note"}],
        )
    yield engine
    engine.dispose()


def test_schema_details_includes_tables_columns_keys_and_samples(
    sqlite_engine: Engine,
) -> None:
    with DatabaseUtil(engine=sqlite_engine) as database:
        details = database.schema_details()

    assert "Table: users" in details
    assert "Table: rides" in details
    assert "Column: name" in details
    assert "Primary Key: id" in details
    assert "Foreign Key: user_id -> users.id" in details
    assert "Sample Data:" in details
    assert "Rider" in details


def test_sample_rows_zero_disables_sampling(sqlite_engine: Engine) -> None:
    database = DatabaseUtil(engine=sqlite_engine)
    try:
        details = database.schema_details(sample_rows=0)
    finally:
        database.dispose()

    assert "Sample Data:" not in details
    assert "Table: users" in details


def test_sample_values_are_truncated(sqlite_engine: Engine) -> None:
    long_value = "x" * 80
    with sqlite_engine.begin() as connection:
        connection.execute(
            Table("users", MetaData(), autoload_with=sqlite_engine).insert().values(
                id=2, name=long_value
            )
        )

    database = DatabaseUtil(engine=sqlite_engine)
    try:
        details = database.schema_details(sample_rows=5)
    finally:
        database.dispose()

    assert "x" * 47 + "..." in details
    assert "x" * 51 not in details


def test_unknown_dialect_is_rejected() -> None:
    with pytest.raises(ValueError, match="postgresql, mysql"):
        load_db_config_from_env({"DB_DIALECT": "sqlite"})


def test_password_with_url_delimiters_round_trips() -> None:
    password = "p@ss:word/value"
    config = load_db_config_from_env(
        {
            "DB_DIALECT": "mysql",
            "DB_HOST": "localhost",
            "DB_PORT": "3306",
            "DB_USER": "agent",
            "DB_PASSWORD": password,
            "DB_NAME": "rides",
        }
    )

    url = config.url
    round_tripped = make_url(url.render_as_string(hide_password=False))

    assert url.drivername == "mysql+pymysql"
    assert url.password == password
    assert round_tripped.password == password


def test_database_object_works_after_multiple_schema_reads(
    sqlite_engine: Engine,
) -> None:
    database = DatabaseUtil(engine=sqlite_engine)
    try:
        first = database.schema_details(sample_rows=0)
        second = database.schema_details(sample_rows=0)
    finally:
        database.dispose()

    assert "Table: users" in first
    assert "Table: rides" in second
