"""Job lifecycle status enum."""

from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    """Lifecycle states for a video job.

    Non-terminal states represent pipeline checkpoints between fetch/process/storage.
    This granularity is used by status sensors to avoid reporting "idle" too early
    while a job is still completing post-processing work.
    """

    CREATED = "created"
    FETCHING = "fetching"
    FETCHED = "fetched"
    PROCESSING = "processing"
    PROCESSED = "processed"
    STORED = "stored"
    DONE = "done"
    FAILED = "failed"
