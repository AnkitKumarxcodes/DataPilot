import csv
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    func,
    select,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.schema import CreateSchema
from sqlalchemy.sql.type_api import TypeEngine

from utils.database import DatabaseUtil, DatabaseConfig, load_db_config_from_env


CSV_DIR = Path(__file__).resolve().parent / "data"
BATCH_SIZE = 1_000
CSV_FILES = {
    "users": "users.csv",
    "vehicles": "vehicles.csv",
    "rides": "rides.csv",
    "payments": "payments.csv",
    "ratings": "ratings.csv",
}


def build_tables(schema_name: str | None) -> tuple[MetaData, dict[str, Table]]:
    """Define the seed tables using types supported by PostgreSQL and MySQL."""
    metadata = MetaData()

    users = Table(
        "users",
        metadata,
        Column("user_id", Integer, primary_key=True),
        Column("first_name", String(100), nullable=False),
        Column("last_name", String(100), nullable=False),
        Column("email", String(255), nullable=False, unique=True),
        Column("phone", String(50)),
        Column("city", String(100)),
        Column("province", String(50)),
        Column("user_type", String(20), nullable=False),
        Column("signup_date", Date),
        Column("is_active", Boolean),
        schema=schema_name,
    )
    vehicles = Table(
        "vehicles",
        metadata,
        Column("vehicle_id", Integer, primary_key=True),
        Column(
            "driver_id",
            Integer,
            ForeignKey(users.c.user_id, name="fk_vehicle_driver"),
            nullable=False,
        ),
        Column("make", String(50)),
        Column("model", String(50)),
        Column("year", Integer),
        Column("license_plate", String(20), unique=True),
        Column("color", String(30)),
        Column("is_active", Boolean),
        schema=schema_name,
    )
    rides = Table(
        "rides",
        metadata,
        Column("ride_id", Integer, primary_key=True),
        Column("rider_id", Integer, ForeignKey(users.c.user_id), nullable=False),
        Column("driver_id", Integer, ForeignKey(users.c.user_id), nullable=False),
        Column("requested_at", DateTime),
        Column("pickup_time", DateTime),
        Column("dropoff_time", DateTime),
        Column("pickup_latitude", Numeric(9, 6)),
        Column("pickup_longitude", Numeric(9, 6)),
        Column("dropoff_latitude", Numeric(9, 6)),
        Column("dropoff_longitude", Numeric(9, 6)),
        Column("distance_km", Numeric(10, 2)),
        Column("fare", Numeric(10, 2)),
        Column("surge_multiplier", Numeric(4, 2)),
        Column("status", String(30)),
        Column("cancellation_reason", String(100)),
        schema=schema_name,
    )
    payments = Table(
        "payments",
        metadata,
        Column("payment_id", Integer, primary_key=True),
        Column("ride_id", Integer, ForeignKey(rides.c.ride_id), nullable=False),
        Column("user_id", Integer, ForeignKey(users.c.user_id), nullable=False),
        Column("amount", Numeric(10, 2)),
        Column("payment_method", String(50)),
        Column("payment_status", String(30)),
        Column("transaction_id", String(100), unique=True),
        Column("payment_time", DateTime),
        schema=schema_name,
    )
    ratings = Table(
        "ratings",
        metadata,
        Column("rating_id", Integer, primary_key=True),
        Column("ride_id", Integer, ForeignKey(rides.c.ride_id), nullable=False),
        Column("rider_id", Integer, ForeignKey(users.c.user_id), nullable=False),
        Column("driver_id", Integer, ForeignKey(users.c.user_id), nullable=False),
        Column("rating", Integer),
        Column("comment", Text),
        Column("rated_at", DateTime),
        CheckConstraint("rating BETWEEN 1 AND 5", name="chk_rating"),
        schema=schema_name,
    )

    Index("idx_vehicles_driver_id", vehicles.c.driver_id)
    Index("idx_rides_rider_id", rides.c.rider_id)
    Index("idx_rides_driver_id", rides.c.driver_id)
    Index("idx_rides_requested_at", rides.c.requested_at)
    Index("idx_rides_status", rides.c.status)
    Index("idx_payments_ride_id", payments.c.ride_id)
    Index("idx_payments_user_id", payments.c.user_id)
    Index("idx_ratings_ride_id", ratings.c.ride_id)
    Index("idx_ratings_driver_id", ratings.c.driver_id)

    return metadata, {
        "users": users,
        "vehicles": vehicles,
        "rides": rides,
        "payments": payments,
        "ratings": ratings,
    }


def parse_csv_value(value: str | None, data_type: TypeEngine[Any]) -> Any:
    """Convert CSV text to Python values accepted by SQLAlchemy drivers."""
    if value is None or value == "":
        return None
    if isinstance(data_type, Boolean):
        normalized = value.strip().lower()
        if normalized in {"true", "t", "yes", "y", "1"}:
            return True
        if normalized in {"false", "f", "no", "n", "0"}:
            return False
        raise ValueError(f"Invalid boolean value in CSV: {value!r}")
    if isinstance(data_type, DateTime):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(data_type, Date):
        return date.fromisoformat(value)
    if isinstance(data_type, Integer):
        return int(value)
    if isinstance(data_type, Numeric):
        return Decimal(value)
    return value


def _read_batches(
    csv_path: Path,
    table: Table,
    batch_size: int,
) -> Iterator[list[dict[str, Any]]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        expected_columns = list(table.c.keys())
        if reader.fieldnames != expected_columns:
            raise ValueError(
                f"CSV columns for {csv_path.name} do not match its table. "
                f"Expected {expected_columns}; found {reader.fieldnames}."
            )

        batch: list[dict[str, Any]] = []
        for row in reader:
            batch.append(
                {
                    column.name: parse_csv_value(
                        row[column.name], column.type
                    )
                    for column in table.columns
                }
            )
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch


def load_csv(
    connection: Connection,
    table: Table,
    csv_path: Path,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Insert one CSV file into its table in bounded batches."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    loaded_rows = 0
    for batch in _read_batches(csv_path, table, batch_size):
        connection.execute(table.insert(), batch)
        loaded_rows += len(batch)
    return loaded_rows


def seed_database(
    engine: Engine,
    dialect: str,
    csv_dir: Path = CSV_DIR,
) -> None:
    """Create the schema, load CSVs, and report table row counts."""
    schema_name = "public" if dialect == "postgresql" else None
    metadata, tables = build_tables(schema_name)

    with engine.begin() as connection:
        if schema_name is not None:
            connection.execute(CreateSchema(schema_name, if_not_exists=True))
        metadata.create_all(connection)
        for table_name, csv_file in CSV_FILES.items():
            loaded = load_csv(connection, tables[table_name], csv_dir / csv_file)
            print(f"Loaded {csv_file} ({loaded:,} rows)")

        print("\nRecord counts:")
        print("-" * 40)
        for table_name, table in tables.items():
            count = connection.scalar(select(func.count()).select_from(table))
            print(f"{table_name:<15} {count:>10,}")


def main() -> None:
    config: DatabaseConfig = load_db_config_from_env()
    with DatabaseUtil(config) as database:
        print(f"Connected to {database.dialect} database.")
        seed_database(database.engine, database.dialect)
    print("\nData loaded successfully.")


if __name__ == "__main__":
    main()
