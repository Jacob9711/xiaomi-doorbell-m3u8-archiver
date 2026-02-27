"""Production adapters for download, processing, and archiving."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

from ..const import META_MOTION_VIDEO_TIME, META_STREAM_URL
from ..core.domain import ArchiveRecord, Artifact, Job, JobStatus, SourceRequest
from ..core.policies import ArchivePolicy


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fetch_bytes_default(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:  # noqa: S310 - user-supplied URL required.
        return response.read()


class HttpM3U8Source:
    """Download remote m3u8 and referenced media segments into local temp directory."""

    def __init__(self, temp_root: Path | None = None, fetch_bytes=None) -> None:
        self._counter = 0
        self._temp_root = temp_root or Path(tempfile.gettempdir()) / "xdma_jobs"
        self._fetch_bytes = fetch_bytes or _fetch_bytes_default

    async def create_job(self, request: SourceRequest) -> Job:
        self._counter += 1
        job_id = f"job-{self._counter:08d}"
        metadata = request.payload.copy()
        metadata["source_type"] = request.source_type
        metadata["dedup_key"] = request.dedup_key
        return Job(job_id=job_id, source_ref=request.source_ref, metadata=metadata)

    async def fetch(self, job: Job) -> Artifact:
        stream_url = str(job.metadata.get(META_STREAM_URL, "")).strip()
        if not stream_url:
            raise ValueError("Missing stream_url in job metadata")

        job_temp = self._temp_root / job.job_id
        await asyncio.to_thread(job_temp.mkdir, parents=True, exist_ok=True)

        m3u8_content = await asyncio.to_thread(self._fetch_bytes, stream_url)
        playlist_lines = m3u8_content.decode("utf-8", errors="replace").splitlines()
        rewritten = []
        segment_index = 0

        for line in playlist_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                rewritten.append(line)
                continue

            segment_url = urljoin(stream_url, stripped)
            ext = Path(urlparse(segment_url).path).suffix or ".ts"
            local_name = f"segment_{segment_index:05d}{ext}"
            segment_path = job_temp / local_name
            segment_bytes = await asyncio.to_thread(self._fetch_bytes, segment_url)
            await asyncio.to_thread(segment_path.write_bytes, segment_bytes)

            rewritten.append(local_name)
            segment_index += 1

        local_playlist = job_temp / "input.m3u8"
        playlist_text = "\n".join(rewritten) + "\n"
        await asyncio.to_thread(local_playlist.write_text, playlist_text, encoding="utf-8")

        return Artifact(
            kind="input",
            uri_or_path=str(local_playlist),
            meta={"job_temp_dir": str(job_temp), "segment_count": segment_index},
        )


@dataclass(slots=True)
class ProcessResult:
    """Internal process execution result."""

    return_code: int
    stderr: str


class FfmpegProcessor:
    """FFmpeg-backed video processor with remux-first strategy."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", runner=None) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._runner = runner or self._run_subprocess

    async def process(self, job: Job, input_artifact: Artifact) -> Artifact:
        input_path = Path(input_artifact.uri_or_path)
        output_path = input_path.parent / "processed.mp4"

        remux_cmd = [
            self._ffmpeg_path,
            "-y",
            "-protocol_whitelist",
            "file,crypto,data,https,tls,tcp",
            "-fflags",
            "+genpts",
            "-i",
            str(input_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        remux_result = await self._runner(remux_cmd)
        if remux_result.return_code == 0:
            return Artifact(
                kind="output",
                uri_or_path=str(output_path),
                meta={"mode": "remux"},
            )

        fallback_cmd = [
            self._ffmpeg_path,
            "-y",
            "-protocol_whitelist",
            "file,crypto,data,https,tls,tcp",
            "-fflags",
            "+genpts",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        fallback_result = await self._runner(fallback_cmd)
        if fallback_result.return_code != 0:
            raise RuntimeError(
                "ffmpeg processing failed; "
                f"remux={remux_result.stderr[-500:]}; fallback={fallback_result.stderr[-500:]}"
            )

        return Artifact(
            kind="output",
            uri_or_path=str(output_path),
            meta={"mode": "transcode_fallback"},
        )

    async def _run_subprocess(self, command: list[str]) -> ProcessResult:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await process.communicate()
        return ProcessResult(return_code=process.returncode or 0, stderr=stderr.decode())


class LocalFsArchive:
    """Store processed output into date-based local archive path."""

    def __init__(self, archive_root: Path) -> None:
        self._archive_root = archive_root
        self._archive_root.mkdir(parents=True, exist_ok=True)

    async def store(self, job: Job, output_artifact: Artifact) -> ArchiveRecord:
        src = Path(output_artifact.uri_or_path)
        if not src.exists():
            raise FileNotFoundError(f"Output artifact not found: {src}")

        event_dt = self._extract_event_time(job)
        subdir = self._archive_root / event_dt.strftime("%Y") / event_dt.strftime("%m") / event_dt.strftime("%d")
        await asyncio.to_thread(subdir.mkdir, parents=True, exist_ok=True)

        source_token = job.source_ref.replace(".", "_").replace(":", "_")
        filename = f"{source_token}_{event_dt.strftime('%Y-%m-%d_%H-%M-%S')}_{job.job_id}.mp4"
        dst = subdir / filename

        await asyncio.to_thread(shutil.move, str(src), str(dst))
        return ArchiveRecord(location=str(dst), meta={"job_id": job.job_id})

    async def apply_policy(self, policy: ArchivePolicy) -> dict:
        if not policy.delete_enabled:
            return {
                "deleted": 0,
                "delete_enabled": False,
                "retention_days": policy.retention_days,
                "active_keep_count": policy.active_keep_count,
            }

        return await asyncio.to_thread(self._apply_policy_sync, policy)

    def _apply_policy_sync(self, policy: ArchivePolicy) -> dict:
        deleted = 0
        files = sorted(self._archive_root.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        now = _utcnow()
        keep_set = set(files[: policy.active_keep_count]) if policy.active_keep_count > 0 else set()
        cutoff = now - timedelta(days=policy.retention_days)

        for path in files:
            if path in keep_set:
                continue
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1

        return {
            "deleted": deleted,
            "delete_enabled": True,
            "retention_days": policy.retention_days,
            "active_keep_count": policy.active_keep_count,
        }

    def _extract_event_time(self, job: Job) -> datetime:
        raw = str(job.metadata.get(META_MOTION_VIDEO_TIME, "")).strip()
        if raw:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        return _utcnow()


class RuntimeRepository:
    """In-memory repository with lightweight metrics updates."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self.total_done = 0
        self.total_failed = 0
        self.last_job_status = JobStatus.CREATED.value

    async def save(self, job: Job) -> None:
        self._jobs[job.job_id] = job
        self.last_job_status = job.status.value

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def update(self, job: Job) -> None:
        old_status = self._jobs[job.job_id].status if job.job_id in self._jobs else None
        self._jobs[job.job_id] = job
        self.last_job_status = job.status.value
        if old_status != JobStatus.DONE and job.status == JobStatus.DONE:
            self.total_done += 1
        if old_status != JobStatus.FAILED and job.status == JobStatus.FAILED:
            self.total_failed += 1

    async def list_incomplete(self) -> list[Job]:
        terminal = {JobStatus.DONE, JobStatus.FAILED}
        return [job for job in self._jobs.values() if job.status not in terminal]
