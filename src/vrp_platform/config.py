"""Platform settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    """Environment-driven platform configuration."""

    environment: str = Field(default="development")
    app_name: str = Field(default="VRP Control Tower")
    timezone: str = Field(default="Asia/Calcutta")
    database_url: str = Field(
        default="sqlite+pysqlite:///./var/vrp_platform.db",
        description="Primary database URL; PostgreSQL in production, SQLite for local dev.",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    use_osrm: bool = Field(default=False)
    osrm_base_url: str = Field(default="http://router.project-osrm.org")
    default_speed_kmh: float = Field(default=32.0)
    rush_hour_multiplier: float = Field(default=1.35)
    demo_live_traffic: bool = Field(default=True)
    default_incident_radius_km: float = Field(default=1.4)
    secret_key: str = Field(default="change-me-in-production")
    driver_demo_id: str = Field(default="driver-demo-1")
    seed_demo_data: bool = Field(default=True)
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(env_prefix="VRP_", case_sensitive=False)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def data_dir(self) -> Path:
        return Path("var")


@lru_cache(maxsize=1)
def get_settings() -> PlatformSettings:
    """Return a cached settings instance."""

    return PlatformSettings()
