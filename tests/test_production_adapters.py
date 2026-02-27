import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from custom_components.xiaomi_doorbell_m3u8_archiver.adapters.production import (
    FfmpegProcessor,
    HttpM3U8Source,
    LocalFsArchive,
    ProcessResult,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.const import (
    META_MOTION_VIDEO_TIME,
    META_STREAM_URL,
)
from custom_components.xiaomi_doorbell_m3u8_archiver.core.domain import Artifact, Job, SourceRequest
from custom_components.xiaomi_doorbell_m3u8_archiver.core.policies import ArchivePolicy


def test_http_m3u8_source_downloads_playlist_and_segments(tmp_path: Path) -> None:
    async def scenario() -> None:
        base_url = "https://example.test/path/clip.m3u8"
        fixtures = {
            base_url: b"#EXTM3U\n#EXTINF:1,\nseg1.ts\n#EXTINF:1,\nsub/seg2.ts\n#EXT-X-ENDLIST\n",
            "https://example.test/path/seg1.ts": b"segment-one",
            "https://example.test/path/sub/seg2.ts": b"segment-two",
        }

        source = HttpM3U8Source(temp_root=tmp_path, fetch_bytes=lambda url: fixtures[url])
        req = SourceRequest(
            source_type="ha_event",
            source_ref="camera.demo",
            payload={META_STREAM_URL: base_url, META_MOTION_VIDEO_TIME: "2026-02-27 08:16:30"},
        )
        job = await source.create_job(req)
        artifact = await source.fetch(job)

        playlist_path = Path(artifact.uri_or_path)
        assert playlist_path.exists()
        text = playlist_path.read_text(encoding="utf-8")
        assert "segment_00000.ts" in text
        assert "segment_00001.ts" in text
        assert (playlist_path.parent / "segment_00000.ts").read_bytes() == b"segment-one"
        assert (playlist_path.parent / "segment_00001.ts").read_bytes() == b"segment-two"

    asyncio.run(scenario())


def test_ffmpeg_processor_fallback_to_transcode(tmp_path: Path) -> None:
    async def scenario() -> None:
        calls: list[list[str]] = []

        async def fake_runner(cmd: list[str]) -> ProcessResult:
            calls.append(cmd)
            if len(calls) == 1:
                return ProcessResult(return_code=1, stderr="remux failed")
            output_path = Path(cmd[-1])
            output_path.write_bytes(b"ok")
            return ProcessResult(return_code=0, stderr="")

        source = HttpM3U8Source(temp_root=tmp_path, fetch_bytes=lambda _: b"#EXTM3U\n")
        req = SourceRequest(
            source_type="manual",
            source_ref="camera.demo",
            payload={META_STREAM_URL: "https://example.test/x.m3u8"},
        )
        job = await source.create_job(req)
        input_path = tmp_path / "input.m3u8"
        input_path.write_text("#EXTM3U\n", encoding="utf-8")

        processor = FfmpegProcessor(ffmpeg_path="ffmpeg", runner=fake_runner)
        artifact = await processor.process(job, Artifact(kind="input", uri_or_path=str(input_path)))

        assert len(calls) == 2
        assert artifact.meta["mode"] == "transcode_fallback"
        assert Path(artifact.uri_or_path).exists()

    asyncio.run(scenario())


def test_local_archive_store_and_policy(tmp_path: Path) -> None:
    async def scenario() -> None:
        archive = LocalFsArchive(tmp_path / "archive")
        job_source = HttpM3U8Source(temp_root=tmp_path / "temp", fetch_bytes=lambda _: b"#EXTM3U\n")
        req = SourceRequest(
            source_type="ha_event",
            source_ref="camera.demo",
            payload={META_MOTION_VIDEO_TIME: "2026-02-27 08:16:30"},
        )
        job = await job_source.create_job(req)

        out_file = tmp_path / "temp" / "processed.mp4"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(b"video")

        record = await archive.store(job, Artifact(kind="output", uri_or_path=str(out_file)))
        stored_path = Path(record.location)
        assert stored_path.exists()
        assert not out_file.exists()

        no_delete = await archive.apply_policy(ArchivePolicy())
        assert no_delete["deleted"] == 0

        old_file = tmp_path / "archive" / "2020" / "01" / "01" / "old.mp4"
        old_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.write_bytes(b"old")
        old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
        os.utime(old_file, (old_ts, old_ts))

        result = await archive.apply_policy(
            ArchivePolicy(active_keep_count=0, retention_days=1, delete_enabled=True)
        )
        assert result["deleted"] >= 1
        assert not old_file.exists()

    asyncio.run(scenario())


def test_ffmpeg_processor_raises_when_both_attempts_fail(tmp_path: Path) -> None:
    async def scenario() -> None:
        async def fake_runner(_: list[str]) -> ProcessResult:
            return ProcessResult(return_code=1, stderr="failed")

        processor = FfmpegProcessor(ffmpeg_path="ffmpeg", runner=fake_runner)
        input_path = tmp_path / "input.m3u8"
        input_path.write_text("#EXTM3U\n", encoding="utf-8")

        with pytest.raises(RuntimeError):
            await processor.process(
                Job(job_id="job-1", source_ref="camera.demo"),
                Artifact(kind="input", uri_or_path=str(input_path)),
            )

    asyncio.run(scenario())
