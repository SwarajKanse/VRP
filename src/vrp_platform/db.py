"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from vrp_platform.config import PlatformSettings


class Base(DeclarativeBase):
    """Base class for ORM models."""


def create_session_factory(settings: PlatformSettings) -> sessionmaker[Session]:
    """Create the session factory for the active database."""

    engine = create_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False} if settings.is_sqlite else {},
    )
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def ensure_schema(engine: Engine) -> None:
    """Apply lightweight compatibility upgrades before the app starts."""

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "vehicles" in table_names:
        columns = {column["name"] for column in inspector.get_columns("vehicles")}
        required_vehicle_columns = {
            "category": "ALTER TABLE vehicles ADD COLUMN category VARCHAR(32) DEFAULT 'VAN' NOT NULL",
            "energy_type": "ALTER TABLE vehicles ADD COLUMN energy_type VARCHAR(16) DEFAULT 'DIESEL' NOT NULL",
            "fuel_consumption_per_km": "ALTER TABLE vehicles ADD COLUMN fuel_consumption_per_km FLOAT DEFAULT 0.12 NOT NULL",
            "energy_unit_cost": "ALTER TABLE vehicles ADD COLUMN energy_unit_cost FLOAT DEFAULT 1.0 NOT NULL",
            "max_continuous_drive_min": "ALTER TABLE vehicles ADD COLUMN max_continuous_drive_min FLOAT DEFAULT 240.0 NOT NULL",
            "required_break_min": "ALTER TABLE vehicles ADD COLUMN required_break_min FLOAT DEFAULT 30.0 NOT NULL",
        }
        missing = [name for name in required_vehicle_columns if name not in columns]
        if missing:
            with engine.begin() as connection:
                for name in missing:
                    connection.execute(text(required_vehicle_columns[name]))
    if "orders" in table_names:
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_external_ref ON orders(external_ref)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_route_plan_id ON orders(route_plan_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_lat_lon ON orders(latitude, longitude)"))


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Context manager for transactional DB access."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
