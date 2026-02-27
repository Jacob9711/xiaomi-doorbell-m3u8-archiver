"""Local filesystem storage adapter."""

from __future__ import annotations

import asyncio
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ...const import META_MOTION_VIDEO_TIME
from ...core.domain import Artifact, Job, StorageRecord
from ...core.policies import RetentionPolicy


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LocalFsStorage:
    """Store processed output into date-based local storage path."""

    def __init__(self, storage_root: Path) -> None:
        self._storage_root = storage_root
        self._storage_root.mkdir(parents=True, exist_ok=True)

    async def store(self, job: Job, output_artifact: Artifact) -> StorageRecord:
        src = Path(output_artifact.uri_or_path)
        if not src.exists():
            raise FileNotFoundError(f"Output artifact not found: {src}")

        event_dt = self._extract_event_time(job)
        # Year/month partitioning keeps long-term storage navigable and avoids huge
        # flat directories that degrade filesystem performance.
        subdir = self._storage_root / event_dt.strftime("%Y") / event_dt.strftime("%m")
        await asyncio.to_thread(subdir.mkdir, parents=True, exist_ok=True)

        source_prefix = self._sanitize_source_ref(job.source_ref)
        base_name = f"{source_prefix}_{event_dt.strftime('%Y_%m_%d_%H_%M_%S')}"
        dst = self._build_non_conflicting_path(subdir, base_name)

        await asyncio.to_thread(shutil.move, str(src), str(dst))
        return StorageRecord(location=str(dst), meta={"job_id": job.job_id})

    def _build_non_conflicting_path(self, folder: Path, base_name: str) -> Path:
        candidate = folder / f"{base_name}.mp4"
        if not candidate.exists():
            return candidate

        suffix = 1
        while True:
            candidate = folder / f"{base_name}_{suffix:02d}.mp4"
            if not candidate.exists():
                return candidate
            suffix += 1

    async def apply_policy(self, policy: RetentionPolicy) -> dict:
        if not policy.delete_enabled:
            return {
                "deleted": 0,
                "delete_enabled": False,
                "retention_days": policy.retention_days,
                "active_keep_count": policy.active_keep_count,
            }
        return await asyncio.to_thread(self._apply_policy_sync, policy)

    def _apply_policy_sync(self, policy: RetentionPolicy) -> dict:
        deleted = 0
        files = sorted(
            self._storage_root.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        now = _utcnow()
        keep_set = set(files[: policy.active_keep_count]) if policy.active_keep_count > 0 else set()
        cutoff = now - timedelta(days=policy.retention_days)

        for path in files:
            # Keep-count has priority over age cutoff so newest footage is retained
            # even when system clocks or source timestamps are imperfect.
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

    def _sanitize_source_ref(self, source_ref: str) -> str:
        # Source refs are entity-like ids (for example camera.xxx); sanitize to keep
        # filenames portable across filesystems while preserving human readability.
        value = re.sub(r"[^A-Za-z0-9_-]+", "_", source_ref.strip())
        value = re.sub(r"_+", "_", value).strip("_")
        return value or "unknown_source"
