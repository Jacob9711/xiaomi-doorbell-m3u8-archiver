"""Mock archive adapter."""

from __future__ import annotations

from ...core.domain import ArchiveRecord, Artifact, Job
from ...core.policies import ArchivePolicy


class MockArchive:
    """In-memory archive for tests."""

    def __init__(self) -> None:
        self.records: list[ArchiveRecord] = []
        self.store_calls = 0
        self.apply_policy_calls = 0

    async def store(self, job: Job, output_artifact: Artifact) -> ArchiveRecord:
        self.store_calls += 1
        record = ArchiveRecord(
            location=f"archive://{job.job_id}/{output_artifact.uri_or_path.split('/')[-1]}"
        )
        self.records.append(record)
        return record

    async def apply_policy(self, policy: ArchivePolicy) -> dict:
        self.apply_policy_calls += 1
        return {
            "active_keep_count": policy.active_keep_count,
            "retention_days": policy.retention_days,
            "delete_enabled": policy.delete_enabled,
        }
