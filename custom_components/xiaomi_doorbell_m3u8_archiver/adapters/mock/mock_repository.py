"""Mock job repository adapter."""

from __future__ import annotations

from ...core.domain import Job, JobStatus


class MockRepository:
    """In-memory job storage for tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    async def save(self, job: Job) -> None:
        self._jobs[job.job_id] = job

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def update(self, job: Job) -> None:
        self._jobs[job.job_id] = job

    async def list_incomplete(self) -> list[Job]:
        terminal = {JobStatus.DONE, JobStatus.FAILED}
        return [job for job in self._jobs.values() if job.status not in terminal]
