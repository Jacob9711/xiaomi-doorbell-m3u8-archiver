"""Pipeline artifact model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Artifact:
    """Artifact produced or consumed in the pipeline.

    `kind` is intentionally a string because adapters define the contract boundary.
    Current core pipeline semantics rely on:
    - "input": fetched local playlist ready for processing.
    - "output": processed media ready for storage.
    """

    kind: str
    uri_or_path: str
    meta: dict[str, Any] = field(default_factory=dict)
