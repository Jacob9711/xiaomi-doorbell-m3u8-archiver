"""Asynchronous pipeline orchestrator."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

from .domain import Artifact, Job, JobStatus, SourceRequest
from .policies import ArchivePolicy, QueuePolicy
from .ports import ArchivePort, JobRepositoryPort, ProcessorPort, SourcePort


class Orchestrator:
    """Coordinate source fetch, processing, and archiving via queue workers."""

    def __init__(
        self,
        source: SourcePort,
        processor: ProcessorPort,
        archive: ArchivePort,
        repository: JobRepositoryPort,
        queue_policy: QueuePolicy | None = None,
        archive_policy: ArchivePolicy | None = None,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        self.source = source
        self.processor = processor
        self.archive = archive
        self.repository = repository
        self.queue_policy = queue_policy or QueuePolicy()
        self.archive_policy = archive_policy or ArchivePolicy()
        self._now_fn = now_fn or time.monotonic

        self.fetch_queue: asyncio.Queue[str | None] = asyncio.Queue(
            maxsize=self.queue_policy.max_queue_size
        )
        self.process_queue: asyncio.Queue[str | None] = asyncio.Queue(
            maxsize=self.queue_policy.max_queue_size
        )

        self._workers: list[asyncio.Task] = []
        self._dedup_index: dict[str, float] = {}
        self._running = False

    async def start(self) -> None:
        """Start background queue workers."""
        if self._running:
            return

        self._running = True
        for _ in range(self.queue_policy.fetch_concurrency):
            self._workers.append(asyncio.create_task(self._fetch_worker()))
        for _ in range(self.queue_policy.process_concurrency):
            self._workers.append(asyncio.create_task(self._process_worker()))

    async def stop(self) -> None:
        """Stop background queue workers gracefully."""
        if not self._running:
            return

        self._running = False
        for _ in range(self.queue_policy.fetch_concurrency):
            await self.fetch_queue.put(None)
        for _ in range(self.queue_policy.process_concurrency):
            await self.process_queue.put(None)

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def enqueue(self, request: SourceRequest) -> Job | None:
        """Create a job and enqueue it to fetch queue if not deduplicated."""
        if request.dedup_key and self._is_duplicate(request.dedup_key):
            return None

        job = await self.source.create_job(request)
        await self.repository.save(job)
        await self.fetch_queue.put(job.job_id)

        if request.dedup_key:
            self._dedup_index[request.dedup_key] = self._now_fn()

        return job

    async def wait_for_idle(self) -> None:
        """Wait until all queued work is completed."""
        await self.fetch_queue.join()
        await self.process_queue.join()

    async def _fetch_worker(self) -> None:
        while True:
            job_id = await self.fetch_queue.get()
            try:
                if job_id is None:
                    return
                await self._run_fetch(job_id)
            finally:
                self.fetch_queue.task_done()

    async def _process_worker(self) -> None:
        while True:
            job_id = await self.process_queue.get()
            try:
                if job_id is None:
                    return
                await self._run_process(job_id)
            finally:
                self.process_queue.task_done()

    async def _run_fetch(self, job_id: str) -> None:
        job = await self.repository.get(job_id)
        if not job:
            return

        while True:
            job.attempts_fetch += 1
            job.transition(JobStatus.FETCHING)
            await self.repository.update(job)

            try:
                input_artifact = await asyncio.wait_for(
                    self.source.fetch(job), timeout=self.queue_policy.fetch_timeout_sec
                )
                job.artifacts["input"] = input_artifact
                job.transition(JobStatus.FETCHED)
                await self.repository.update(job)
                await self.process_queue.put(job.job_id)
                return
            except Exception as exc:  # noqa: BLE001 - store pipeline failures.
                if job.attempts_fetch > self.queue_policy.retry_limit:
                    job.error = str(exc)
                    job.transition(JobStatus.FAILED)
                    await self.repository.update(job)
                    return

                await asyncio.sleep(self.queue_policy.retry_backoff_sec)

    async def _run_process(self, job_id: str) -> None:
        job = await self.repository.get(job_id)
        if not job:
            return

        input_artifact = job.artifacts.get("input")
        if input_artifact is None:
            job.error = "Missing input artifact"
            job.transition(JobStatus.FAILED)
            await self.repository.update(job)
            return

        while True:
            job.attempts_process += 1
            job.transition(JobStatus.PROCESSING)
            await self.repository.update(job)

            try:
                output_artifact = await asyncio.wait_for(
                    self.processor.process(job, input_artifact),
                    timeout=self.queue_policy.process_timeout_sec,
                )
                job.artifacts["output"] = output_artifact
                job.transition(JobStatus.PROCESSED)
                await self.repository.update(job)

                archive_record = await self.archive.store(job, output_artifact)
                job.metadata["archive"] = {
                    "location": archive_record.location,
                    "archived_at": archive_record.archived_at.isoformat(),
                }
                job.transition(JobStatus.ARCHIVED)
                await self.repository.update(job)

                await self.archive.apply_policy(self.archive_policy)
                job.transition(JobStatus.DONE)
                await self.repository.update(job)
                return
            except Exception as exc:  # noqa: BLE001 - store pipeline failures.
                if job.attempts_process > self.queue_policy.retry_limit:
                    job.error = str(exc)
                    job.transition(JobStatus.FAILED)
                    await self.repository.update(job)
                    return

                await asyncio.sleep(self.queue_policy.retry_backoff_sec)

    def _is_duplicate(self, dedup_key: str) -> bool:
        self._cleanup_dedup_index()
        last_seen = self._dedup_index.get(dedup_key)
        if last_seen is None:
            return False
        return (self._now_fn() - last_seen) < self.queue_policy.dedup_window_sec

    def _cleanup_dedup_index(self) -> None:
        cutoff = self._now_fn() - self.queue_policy.dedup_window_sec
        stale_keys = [k for k, seen in self._dedup_index.items() if seen < cutoff]
        for key in stale_keys:
            del self._dedup_index[key]
