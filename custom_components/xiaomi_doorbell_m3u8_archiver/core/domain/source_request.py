"""Source request value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceRequest:
    """Input request from a source adapter.

    `source_type` separates event-driven ingestion ("ha_event") from manual calls
    ("manual"). The coordinator intentionally applies different motion-cursor rules
    based on this value.
    """

    source_type: str
    source_ref: str
    payload: dict[str, Any] = field(default_factory=dict)
