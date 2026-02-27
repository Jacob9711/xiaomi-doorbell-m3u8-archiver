import asyncio

from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.mock.mock_storage import MockStorage
from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.mock.mock_processor import (
    MockProcessor,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.mock.mock_source import MockSource
from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.repository.runtime_repository import (
    RuntimeRepository,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.core.domain import Job, JobStatus
from custom_components.xiaomi_doorbell_m3u8_archiver.core.orchestration.orchestrator import (
    Orchestrator,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.ha_integration.coordinator import (
    IntegrationRuntime,
)


def test_metrics_report_idle_and_busy_states() -> None:
    # Intent: queue depth should drive visible busy/idle state.
    # Expect: empty queues => idle, queued fetch work => busy.
    async def scenario() -> None:
        repo = RuntimeRepository()
        orchestrator = Orchestrator(MockSource(), MockProcessor(), MockStorage(), repo)
        runtime = IntegrationRuntime(
            orchestrator=orchestrator, repository=repo, storage=MockStorage()
        )

        metrics_idle = runtime.metrics()
        assert metrics_idle["current_job_status"] == metrics_idle["last_job_status"]
        assert metrics_idle["is_busy"] is False
        assert metrics_idle["processed_today"] == 0

        await orchestrator.fetch_queue.put("job-1")
        metrics_busy = runtime.metrics()
        assert metrics_busy["is_busy"] is True

        _ = await orchestrator.fetch_queue.get()
        orchestrator.fetch_queue.task_done()

    asyncio.run(scenario())


def test_processed_today_increments_when_done() -> None:
    # Intent: repository counters must reflect terminal DONE transitions.
    # Expect: total_done and processed_today increment together.
    async def scenario() -> None:
        repo = RuntimeRepository()
        job = Job(job_id="job-1", source_ref="camera.demo")
        await repo.save(job)
        job.transition(JobStatus.DONE)
        await repo.update(job)

        assert repo.total_done == 1
        assert repo.processed_today == 1

    asyncio.run(scenario())


def test_metrics_busy_for_inflight_terminal_transition_statuses() -> None:
    # Intent: transitional statuses should not report idle too early.
    # Expect: STORED reports busy, DONE reports idle.
    async def scenario() -> None:
        repo = RuntimeRepository()
        orchestrator = Orchestrator(MockSource(), MockProcessor(), MockStorage(), repo)
        runtime = IntegrationRuntime(
            orchestrator=orchestrator, repository=repo, storage=MockStorage()
        )

        repo.last_job_status = JobStatus.STORED.value
        metrics_stored = runtime.metrics()
        assert metrics_stored["current_job_status"] == JobStatus.STORED.value
        assert metrics_stored["is_busy"] is True

        repo.last_job_status = JobStatus.DONE.value
        metrics_done = runtime.metrics()
        assert metrics_done["current_job_status"] == JobStatus.DONE.value
        assert metrics_done["is_busy"] is False

    asyncio.run(scenario())
