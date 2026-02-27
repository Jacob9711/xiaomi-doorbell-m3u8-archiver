"""Process execution result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProcessResult:
    """Internal process execution result."""

    return_code: int
    stderr: str
