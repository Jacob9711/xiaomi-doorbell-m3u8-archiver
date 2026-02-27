"""Asynchronous pipeline orchestrator."""

from __future__ import annotations

import asyncio

from ..domain import Job, JobStatus, SourceRequest
from ..lifecycle import JobContext, attach_job_context
from ..policies import QueuePolicy, RetentionPolicy
from ..ports import JobRepositoryPort, ProcessorPort, SourcePort, StoragePort


class Orchestrator:
    """Coordinate source fetch, processing, and storage via queue workers.

    Fetch and process are isolated into two queues so network variability does not
    directly stall CPU-heavy ffmpeg work, and vice versa.
    """

    def __init__(
        self,
        source: SourcePort,
        processor: ProcessorPort,
        storage: StoragePort,
        repository: JobRepositoryPort,
        queue_policy: QueuePolicy | None = None,
        retention_policy: RetentionPolicy | None = None,
    ) -> None:
        self.source = source
        self.processor = processor
        self.storage = storage
        self.repository = repository
        self.queue_policy = queue_policy or QueuePolicy()
        self.retention_policy = retention_policy or RetentionPolicy()

        self.fetch_queue: asyncio.Queue[str | None] = asyncio.Queue(
            maxsize=self.queue_policy.max_queue_size
        )
        self.process_queue: asyncio.Queue[str | None] = asyncio.Queue(
            maxsize=self.queue_policy.max_queue_size
        )

        self._workers: list[asyncio.Task] = []
        self._job_contexts: dict[str, JobContext] = {}
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
        """Create a job and enqueue it to fetch queue."""
        job = await self.source.create_job(request)
        context = JobContext(job_id=job.job_id)
        attach_job_context(job, context)
        self._job_contexts[job.job_id] = context
        await self.repository.save(job)
        await self.fetch_queue.put(job.job_id)
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
            await self._finalize_job_context(job_id)
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
            except Exception as exc:  # noqa: BLE001
                # Retry policy is managed here so source adapters stay simple and
                # the same backoff semantics apply across all implementations.
                if job.attempts_fetch > self.queue_policy.retry_limit:
                    job.error = str(exc)
                    job.transition(JobStatus.FAILED)
                    await self.repository.update(job)
                    await self._finalize_job_context(job.job_id)
                    return
                await asyncio.sleep(self.queue_policy.retry_backoff_sec)

    async def _run_process(self, job_id: str) -> None:
        job = await self.repository.get(job_id)
        if not job:
            await self._finalize_job_context(job_id)
            return

        try:
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

                    storage_record = await self.storage.store(job, output_artifact)
                    job.metadata["storage"] = {
                        "location": storage_record.location,
                        "stored_at": storage_record.stored_at.isoformat(),
                    }
                    job.transition(JobStatus.STORED)
                    await self.repository.update(job)

                    await self.storage.apply_policy(self.retention_policy)
                    # DONE is emitted only after policy maintenance so sensors and
                    # service responses treat the storage step as fully completed.
                    job.transition(JobStatus.DONE)
                    await self.repository.update(job)
                    return
                except Exception as exc:  # noqa: BLE001
                    if job.attempts_process > self.queue_policy.retry_limit:
                        job.error = str(exc)
                        job.transition(JobStatus.FAILED)
                        await self.repository.update(job)
                        return
                    await asyncio.sleep(self.queue_policy.retry_backoff_sec)
        finally:
            # Cleanup runs exactly once at orchestration boundary, regardless of
            # success, retries exhausted, or unexpected exceptions.
            await self._finalize_job_context(job_id)

    async def _finalize_job_context(self, job_id: str) -> None:
        context = self._job_contexts.pop(job_id, None)
        if context is not None:
            await context.cleanup_all()
