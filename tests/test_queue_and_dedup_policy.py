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
from custom_components.xiaomi_doorbell_m3u8_archiver.core.domain import SourceRequest
from custom_components.xiaomi_doorbell_m3u8_archiver.core.orchestrator import Orchestrator
from custom_components.xiaomi_doorbell_m3u8_archiver.core.policies import QueuePolicy


def test_dedup_and_process_single_concurrency() -> None:
    async def scenario() -> None:
        source = MockSource()
        processor = MockProcessor(process_delay_sec=0.01)
        archive = MockArchive()
        repo = MockRepository()
        policy = QueuePolicy(
            fetch_concurrency=2,
            process_concurrency=1,
            dedup_window_sec=60,
            retry_backoff_sec=0.001,
        )
        orchestrator = Orchestrator(source, processor, archive, repo, queue_policy=policy)

        await orchestrator.start()
        try:
            req = SourceRequest(
                source_type="ha_event",
                source_ref="camera.demo",
                dedup_key="camera.demo:12345",
            )
            job1 = await orchestrator.enqueue(req)
            job2 = await orchestrator.enqueue(req)
            assert job1 is not None
            assert job2 is None

            for i in range(5):
                await orchestrator.enqueue(
                    SourceRequest(
                        source_type="manual",
                        source_ref=f"manual://{i}",
                        dedup_key=f"manual:{i}",
                    )
                )

            await orchestrator.wait_for_idle()
            assert processor.max_active == 1
        finally:
            await orchestrator.stop()

    asyncio.run(scenario())
