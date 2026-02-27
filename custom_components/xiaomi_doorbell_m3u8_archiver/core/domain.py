"""Core domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    """Lifecycle states for a video job."""

    CREATED = "created"
    FETCHING = "fetching"
    FETCHED = "fetched"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ARCHIVED = "archived"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class SourceRequest:
    """Input request from a source adapter."""

    source_type: str
    source_ref: str
    payload: dict[str, Any] = field(default_factory=dict)
    dedup_key: str | None = None


@dataclass(slots=True)
class Artifact:
    """Artifact produced or consumed in the pipeline."""

    kind: str
    uri_or_path: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ArchiveRecord:
    """Archive result record."""

    location: str
    archived_at: datetime = field(default_factory=utcnow)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Job:
    """Pipeline job aggregate root."""

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
