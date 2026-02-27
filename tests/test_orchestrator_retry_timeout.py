import asyncio

from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.mock.mock_archive import (
    MockArchive,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.mock.mock_processor import (
    MockProcessor,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.mock.mock_repository import (
    MockRepository,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.mock.mock_source import (
    MockSource,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.core.domain import (
    JobStatus,
    SourceRequest,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.core.orchestrator import Orchestrator
from custom_components.xiaomi_doorbell_m3u8_archiver.core.policies import QueuePolicy


def test_retry_then_success() -> None:
    async def scenario() -> None:
        source = MockSource(fail_fetch_times=1)
        processor = MockProcessor(fail_process_times=1)
        archive = MockArchive()
        repo = MockRepository()
        policy = QueuePolicy(retry_limit=1, retry_backoff_sec=0.001)
        orchestrator = Orchestrator(source, processor, archive, repo, queue_policy=policy)

        await orchestrator.start()
        try:
            job = await orchestrator.enqueue(
                SourceRequest(source_type="ha_event", source_ref="camera.demo")
            )
            assert job is not None
            await orchestrator.wait_for_idle()

            saved = await repo.get(job.job_id)
            assert saved is not None
            assert saved.status == JobStatus.DONE
            assert saved.attempts_fetch == 2
            assert saved.attempts_process == 2
        finally:
            await orchestrator.stop()

    asyncio.run(scenario())


def test_timeout_leads_to_failed_job() -> None:
    async def scenario() -> None:
        source = MockSource(fetch_delay_sec=0.02)
        processor = MockProcessor()
        archive = MockArchive()
        repo = MockRepository()
        policy = QueuePolicy(
            retry_limit=0,
            fetch_timeout_sec=0.001,
            retry_backoff_sec=0.001,
        )
        orchestrator = Orchestrator(source, processor, archive, repo, queue_policy=policy)

        await orchestrator.start()
        try:
            job = await orchestrator.enqueue(
                SourceRequest(source_type="ha_event", source_ref="camera.demo")
            )
            assert job is not None
            await orchestrator.wait_for_idle()

            saved = await repo.get(job.job_id)
            assert saved is not None
            assert saved.status == JobStatus.FAILED
            assert saved.error is not None
        finally:
            await orchestrator.stop()

    asyncio.run(scenario())
