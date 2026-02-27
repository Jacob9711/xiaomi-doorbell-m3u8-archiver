"""Port interfaces for pluggable adapters."""

from __future__ import annotations

from typing import Protocol

from .domain import ArchiveRecord, Artifact, Job, SourceRequest
from .policies import ArchivePolicy


class SourcePort(Protocol):
    """Source adapter interface."""

    async def create_job(self, request: SourceRequest) -> Job:
        """Create a Job from an incoming source request."""

    async def fetch(self, job: Job) -> Artifact:
        """Fetch source media and produce input artifact."""


class ProcessorPort(Protocol):
    """Processor adapter interface."""

    async def process(self, job: Job, input_artifact: Artifact) -> Artifact:
        """Transform source artifact into output artifact."""


class ArchivePort(Protocol):
    """Archive adapter interface."""

    async def store(self, job: Job, output_artifact: Artifact) -> ArchiveRecord:
        """Persist output artifact to archive backend."""

    async def apply_policy(self, policy: ArchivePolicy) -> dict:
        """Apply archive policy maintenance."""


class JobRepositoryPort(Protocol):
    """Persistence adapter for job state."""

    async def save(self, job: Job) -> None:
        """Persist a newly created job."""

    async def get(self, job_id: str) -> Job | None:
        """Read an existing job."""

    async def update(self, job: Job) -> None:
        """Persist a job state update."""

    async def list_incomplete(self) -> list[Job]:
        """List jobs not in terminal state."""
