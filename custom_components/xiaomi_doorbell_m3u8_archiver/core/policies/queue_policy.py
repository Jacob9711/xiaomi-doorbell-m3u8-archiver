"""Queue policy model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class QueuePolicy:
    """Queue and retry policy.

    These values are operational controls: they cap memory pressure, bound time spent
    on stuck IO/ffmpeg calls, and define how aggressive retries should be.
    """

    fetch_concurrency: int = 2
    process_concurrency: int = 1
    max_queue_size: int = 200
    retry_limit: int = 1
    retry_backoff_sec: float = 0.01
    fetch_timeout_sec: float = 10.0
    process_timeout_sec: float = 60.0
