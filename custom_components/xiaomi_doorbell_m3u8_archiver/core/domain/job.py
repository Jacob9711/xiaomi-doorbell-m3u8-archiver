"""Job aggregate model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .artifact import Artifact
from .job_status import JobStatus
from .time_utils import utcnow


@dataclass(slots=True)
class Job:
    """Pipeline job aggregate root.

    Job keeps both the current state and full transition history so runtime metrics
    and troubleshooting can reason about retries and where a job failed.
    """

    job_id: str
    source_ref: str
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    attempts_fetch: int = 0
    attempts_process: int = 0
    error: str | None = None
    history: list[JobStatus] = field(default_factory=lambda: [JobStatus.CREATED])

    def transition(self, new_status: JobStatus) -> None:
        """Apply a status transition and update timestamps."""
        self.status = new_status
        self.updated_at = utcnow()
        self.history.append(new_status)
