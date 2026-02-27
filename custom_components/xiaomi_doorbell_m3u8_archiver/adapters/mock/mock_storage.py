"""Mock storage adapter."""

from __future__ import annotations

from ...core.domain import Artifact, Job, StorageRecord
from ...core.policies import RetentionPolicy


class MockStorage:
    """In-memory storage for tests."""

    def __init__(self) -> None:
        self.records: list[StorageRecord] = []
        self.store_calls = 0
        self.apply_policy_calls = 0

    async def store(self, job: Job, output_artifact: Artifact) -> StorageRecord:
        self.store_calls += 1
        record = StorageRecord(
            location=f"storage://{job.job_id}/{output_artifact.uri_or_path.split('/')[-1]}"
        )
        self.records.append(record)
        return record

    async def apply_policy(self, policy: RetentionPolicy) -> dict:
        self.apply_policy_calls += 1
        return {
            "active_keep_count": policy.active_keep_count,
            "retention_days": policy.retention_days,
            "delete_enabled": policy.delete_enabled,
        }
