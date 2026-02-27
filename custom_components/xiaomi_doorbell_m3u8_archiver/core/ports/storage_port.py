"""Storage adapter interface."""

from __future__ import annotations

from typing import Protocol

from ..domain import Artifact, Job, StorageRecord
from ..policies import RetentionPolicy


class StoragePort(Protocol):
    """Storage adapter interface."""

    async def store(self, job: Job, output_artifact: Artifact) -> StorageRecord:
        """Persist output artifact to storage backend."""

    async def apply_policy(self, policy: RetentionPolicy) -> dict:
        """Apply retention policy maintenance."""
