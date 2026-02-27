from custom_components.xiaomi_doorbell_m3u8_archiver.ha_integration.resolver import (
    build_source_request,
)


def test_build_source_request_success_with_motion_time() -> None:
    request = build_source_request(
        entity_id="camera.loock",
        attributes={
            "stream_address": "https://example.com/live.m3u8",
            "motion_video_time": "2026-02-27T11:12:13",
        },
        source_type="ha_event",
    )
    assert request is not None
    assert request.source_ref == "camera.loock"
    assert request.payload["stream_url"] == "https://example.com/live.m3u8"
    assert request.payload["motion_video_time"] == "2026-02-27T11:12:13"
    assert request.dedup_key == "camera.loock:2026-02-27T11:12:13"


def test_build_source_request_supports_event_override() -> None:
    request = build_source_request(
        entity_id="camera.loock",
        attributes={"stream_address": "https://example.com/live.m3u8"},
        source_type="manual",
        event_time="custom-event-time",
    )
    assert request is not None
    assert request.payload["motion_video_time"] == "custom-event-time"
    assert request.dedup_key == "camera.loock:custom-event-time"


def test_build_source_request_returns_none_without_stream_address() -> None:
    request = build_source_request(
        entity_id="camera.loock",
        attributes={"motion_video_time": "2026-02-27T11:12:13"},
        source_type="ha_event",
    )
    assert request is None
