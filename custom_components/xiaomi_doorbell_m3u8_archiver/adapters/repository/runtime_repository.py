"""In-memory runtime job repository."""

from __future__ import annotations

from datetime import datetime, timezone

from ...core.domain import Job, JobStatus


class RuntimeRepository:
    """In-memory repository with lightweight metrics updates."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._status_snapshot: dict[str, JobStatus] = {}
        self.total_done = 0
        self.total_failed = 0
        self.processed_today = 0
        self._processed_day_key = self._day_key()
        self.last_job_status = JobStatus.CREATED.value

    async def save(self, job: Job) -> None:
        self._jobs[job.job_id] = job
        self._status_snapshot[job.job_id] = job.status
        self.last_job_status = job.status.value

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def update(self, job: Job) -> None:
        self._rollover_processed_today_if_needed()
        old_status = self._status_snapshot.get(job.job_id)
        self._jobs[job.job_id] = job
        self._status_snapshot[job.job_id] = job.status
        self.last_job_status = job.status.value
        if old_status != JobStatus.DONE and job.status == JobStatus.DONE:
            self.total_done += 1
            self.processed_today += 1
        if old_status != JobStatus.FAILED and job.status == JobStatus.FAILED:
            self.total_failed += 1

    async def list_incomplete(self) -> list[Job]:
        terminal = {JobStatus.DONE, JobStatus.FAILED}
        return [job for job in self._jobs.values() if job.status not in terminal]

    def _day_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _rollover_processed_today_if_needed(self) -> None:
        current = self._day_key()
        if current != self._processed_day_key:
            self._processed_day_key = current
            self.processed_today = 0
