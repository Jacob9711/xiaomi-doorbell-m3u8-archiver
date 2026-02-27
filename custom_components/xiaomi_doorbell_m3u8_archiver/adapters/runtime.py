"""Runtime adapters used by Home Assistant integration layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..const import META_STREAM_URL
from ..core.domain import ArchiveRecord, Artifact, Job, JobStatus, SourceRequest
from ..core.policies import ArchivePolicy


class RuntimeSource:
    """Simple source adapter creating jobs from incoming requests."""

    def __init__(self) -> None:
        self._counter = 0

    async def create_job(self, request: SourceRequest) -> Job:
        self._counter += 1
        job_id = f"job-{self._counter:08d}"
        metadata = request.payload.copy()
        metadata["source_type"] = request.source_type
        metadata["dedup_key"] = request.dedup_key
        return Job(job_id=job_id, source_ref=request.source_ref, metadata=metadata)

    async def fetch(self, job: Job) -> Artifact:
        stream_url = str(job.metadata.get(META_STREAM_URL, ""))
        uri = stream_url if stream_url else f"source://{job.source_ref}"
        return Artifact(kind="input", uri_or_path=uri, meta={"job_id": job.job_id})


class RuntimeProcessor:
    """Placeholder processor returning a deterministic output artifact."""

    async def process(self, job: Job, input_artifact: Artifact) -> Artifact:
        return Artifact(
            kind="output",
            uri_or_path=f"processed://{job.job_id}.mp4",
            meta={"input": input_artifact.uri_or_path},
        )


class RuntimeArchive:
    """In-memory archive tracking stored artifacts."""

    def __init__(self) -> None:
        self.records: list[ArchiveRecord] = []
        self.last_policy_result: dict[str, Any] = {}

    async def store(self, job: Job, output_artifact: Artifact) -> ArchiveRecord:
        record = ArchiveRecord(
            location=f"archive://{job.job_id}/{output_artifact.uri_or_path.split('/')[-1]}"
        )
        self.records.append(record)
        return record

    async def apply_policy(self, policy: ArchivePolicy) -> dict:
        self.last_policy_result = {
            "active_keep_count": policy.active_keep_count,
            "retention_days": policy.retention_days,
            "delete_enabled": policy.delete_enabled,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.last_policy_result


class RuntimeRepository:
    """In-memory repository with lightweight metrics updates."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self.total_done = 0
        self.total_failed = 0
        self.last_job_status = JobStatus.CREATED.value

    async def save(self, job: Job) -> None:
        self._jobs[job.job_id] = job
        self.last_job_status = job.status.value

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def update(self, job: Job) -> None:
        old_status = self._jobs[job.job_id].status if job.job_id in self._jobs else None
        self._jobs[job.job_id] = job
        self.last_job_status = job.status.value
        if old_status != JobStatus.DONE and job.status == JobStatus.DONE:
            self.total_done += 1
        if old_status != JobStatus.FAILED and job.status == JobStatus.FAILED:
            self.total_failed += 1

    async def list_incomplete(self) -> list[Job]:
        terminal = {JobStatus.DONE, JobStatus.FAILED}
        return [job for job in self._jobs.values() if job.status not in terminal]
