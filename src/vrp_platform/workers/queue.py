"""RQ queue helpers."""

from __future__ import annotations

from redis import Redis
from rq import Queue

from vrp_platform.config import PlatformSettings


def create_queue(settings: PlatformSettings, name: str = "vrp") -> Queue:
    """Return an RQ queue for background jobs."""

    connection = Redis.from_url(settings.redis_url)
    return Queue(name, connection=connection)

