"""Runtime coordinator for Home Assistant integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..adapters.runtime import RuntimeArchive, RuntimeProcessor, RuntimeRepository, RuntimeSource
from ..core.domain import Job, SourceRequest
from ..core.orchestrator import Orchestrator
from ..core.policies import ArchivePolicy, QueuePolicy


@dataclass(slots=True)
class IntegrationRuntime:
    """Encapsulate running orchestrator and adapters."""

    orchestrator: Orchestrator
    repository: RuntimeRepository
    archive: RuntimeArchive
    unsub_listener: Any = None

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "IntegrationRuntime":
        """Build runtime from integration config."""
        queue_policy = QueuePolicy(
            fetch_concurrency=cfg["fetch_concurrency"],
            process_concurrency=cfg["process_concurrency"],
            max_queue_size=cfg["max_queue_size"],
            dedup_window_sec=cfg["dedup_window_sec"],
            retry_limit=cfg["retry_limit"],
            retry_backoff_sec=cfg["retry_backoff_sec"],
        )
        archive_policy = ArchivePolicy()
        source = RuntimeSource()
        processor = RuntimeProcessor()
        archive = RuntimeArchive()
        repository = RuntimeRepository()
        orchestrator = Orchestrator(
            source=source,
            processor=processor,
            archive=archive,
            repository=repository,
            queue_policy=queue_policy,
            archive_policy=archive_policy,
        )
        return cls(orchestrator=orchestrator, repository=repository, archive=archive)

    async def start(self) -> None:
        """Start orchestrator workers."""
        await self.orchestrator.start()

    async def stop(self) -> None:
        """Stop listener and orchestrator workers."""
        if self.unsub_listener:
            self.unsub_listener()
            self.unsub_listener = None
        await self.orchestrator.stop()

    async def enqueue_request(self, request: SourceRequest) -> Job | None:
        """Enqueue a source request."""
        return await self.orchestrator.enqueue(request)

    def metrics(self) -> dict[str, Any]:
        """Return in-memory metrics for sensor entities."""
        return {
            "total_done": self.repository.total_done,
            "total_failed": self.repository.total_failed,
            "queue_fetch_size": self.orchestrator.fetch_queue.qsize(),
            "queue_process_size": self.orchestrator.process_queue.qsize(),
            "last_job_status": self.repository.last_job_status,
        }
