from custom_components.xiaomi_doorbell_m3u8_archiver.core.domain import (
    Artifact,
    Job,
    JobStatus,
    SourceRequest,
)


def test_source_request_defaults() -> None:
    req = SourceRequest(source_type="ha_event", source_ref="camera.demo")
    assert req.payload == {}


def test_job_transition_and_history() -> None:
    job = Job(job_id="job-1", source_ref="source://test")
    assert job.status == JobStatus.CREATED
    assert job.history == [JobStatus.CREATED]

    job.transition(JobStatus.FETCHING)
    job.transition(JobStatus.FETCHED)
    job.artifacts["input"] = Artifact(kind="input", uri_or_path="mem://in")

    assert job.status == JobStatus.FETCHED
    assert job.history[-2:] == [JobStatus.FETCHING, JobStatus.FETCHED]
    assert job.artifacts["input"].uri_or_path == "mem://in"
