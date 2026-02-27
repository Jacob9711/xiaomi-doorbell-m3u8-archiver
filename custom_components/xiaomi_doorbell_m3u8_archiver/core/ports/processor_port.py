"""Processor adapter interface."""

from __future__ import annotations

from typing import Protocol

from ..domain import Artifact, Job


class ProcessorPort(Protocol):
    """Processor adapter interface."""

    async def process(self, job: Job, input_artifact: Artifact) -> Artifact:
        """Transform source artifact into output artifact."""
