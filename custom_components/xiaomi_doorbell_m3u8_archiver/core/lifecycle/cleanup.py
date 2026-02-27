"""Job lifecycle cleanup primitives."""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..domain import Job

JOB_CONTEXT_META_KEY = "_job_context"


class CleanupHandle(Protocol):
    """A cleanup action bound to one job."""

    name: str

    async def cleanup(self) -> None:
        """Release resources owned by this handle."""


@dataclass(slots=True)
class JobContext:
    """Track cleanup actions for a single job lifecycle."""

    job_id: str
    _cleanup_handles: list[CleanupHandle] = field(default_factory=list)

    def register_cleanup(self, handle: CleanupHandle) -> CleanupHandle:
        """Register a cleanup handle and return it."""
        self._cleanup_handles.append(handle)
        return handle

    def unregister_cleanup(self, handle: CleanupHandle) -> None:
        """Unregister a handle if it has already been released."""
        try:
            self._cleanup_handles.remove(handle)
        except ValueError:
            return

    async def cleanup_all(self) -> None:
        """Run all cleanup handles in reverse registration order."""
        for handle in reversed(self._cleanup_handles):
            try:
                await handle.cleanup()
            except Exception:  # noqa: BLE001 - cleanup should be best-effort.
                continue
        self._cleanup_handles.clear()


@dataclass(slots=True)
class DirectoryCleanupHandle:
    """Cleanup handle for temporary directories."""

    path: Path
    name: str = "directory"

    async def cleanup(self) -> None:
        await asyncio.to_thread(shutil.rmtree, self.path, True)


@dataclass(slots=True)
class FileCleanupHandle:
    """Cleanup handle for temporary files."""

    path: Path
    name: str = "file"

    async def cleanup(self) -> None:
        await asyncio.to_thread(self.path.unlink, True)


@dataclass(slots=True)
class ProcessCleanupHandle:
    """Cleanup handle for async subprocesses."""

    process: asyncio.subprocess.Process
    name: str = "process"

    async def cleanup(self) -> None:
        if self.process.returncode is not None:
            return
        self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=3)
        except asyncio.TimeoutError:
            self.process.kill()
            await self.process.wait()


def attach_job_context(job: Job, context: JobContext) -> None:
    """Attach job context to job metadata."""
    job.metadata[JOB_CONTEXT_META_KEY] = context


def get_job_context(job: Job) -> JobContext | None:
    """Get attached job context from metadata."""
    context = job.metadata.get(JOB_CONTEXT_META_KEY)
    if isinstance(context, JobContext):
        return context
    return None
