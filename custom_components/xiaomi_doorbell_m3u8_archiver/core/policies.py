"""Core policy objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class QueuePolicy:
    """Queue and retry policy."""

    fetch_concurrency: int = 2
    process_concurrency: int = 1
    max_queue_size: int = 200
    dedup_window_sec: int = 60
    retry_limit: int = 1
    retry_backoff_sec: float = 0.01
    fetch_timeout_sec: float = 10.0
    process_timeout_sec: float = 60.0


@dataclass(slots=True)
class ArchivePolicy:
    """Archive retention behavior."""

    active_keep_count: int = 30
    retention_days: int = 3650
    delete_enabled: bool = False
