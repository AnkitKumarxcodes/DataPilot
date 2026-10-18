import csv
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine

from feed_db import build_tables, seed_database


def _write_csv(directory: Path, filename: str, row: dict[str, str]) -> None:
    with (directory / filename).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def test_seed_database_loads_all_csvs_with_sqlite(tmp_path: Path) -> None:
    rows = {
        "users.csv": {
            "user_id": "1",
            "first_name": "Sample",
            "last_name": "Rider",
            "email": "sample@example.test",
            "phone": "",
            "city": "Toronto",
            "province": "ON",
            "user_type": "rider",
            "signup_date": "2024-01-01",
            "is_active": "true",
        },
        "vehicles.csv": {
            "vehicle_id": "1",
            "driver_id": "1",
            "make": "Example",
            "model": "Car",
            "year": "2020",
            "license_plate": "TEST-1",
            "color": "blue",
            "is_active": "false",
        },
        "rides.csv": {
            "ride_id": "1",
            "rider_id": "1",
            "driver_id": "1",
            "requested_at": "2024-01-01T10:00:00",
            "pickup_time": "2024-01-01T10:05:00",
            "dropoff_time": "2024-01-01T10:25:00",
            "pickup_latitude": "43.653200",
            "pickup_longitude": "-79.383200",
            "dropoff_latitude": "43.700000",
            "dropoff_longitude": "-79.400000",
            "distance_km": "5.25",
            "fare": "14.50",
            "surge_multiplier": "1.00",
            "status": "completed",
            "cancellation_reason": "",
        },
        "payments.csv": {
            "payment_id": "1",
            "ride_id": "1",
            "user_id": "1",
            "amount": "14.50",
            "payment_method": "card",
            "payment_status": "paid",
            "transaction_id": "transaction-1",
            "payment_time": "2024-01-01T10:26:00",
        },
        "ratings.csv": {
            "rating_id": "1",
            "ride_id": "1",
            "rider_id": "1",
            "driver_id": "1",
            "rating": "5",
            "comment": "Good ride",
            "rated_at": "2024-01-01T10:30:00",
        },
    }
    for filename, row in rows.items():
        _write_csv(tmp_path, filename, row)

    engine: Engine = create_engine("sqlite:///:memory:")
    try:
        seed_database(engine, "mysql", tmp_path)

        _, tables = build_tables(None)
        with engine.connect() as connection:
            counts = {
                name: connection.scalar(select(func.count()).select_from(table))
                for name, table in tables.items()
            }
    finally:
        engine.dispose()

    assert counts == {
        "users": 1,
        "vehicles": 1,
        "rides": 1,
        "payments": 1,
        "ratings": 1,
    }
