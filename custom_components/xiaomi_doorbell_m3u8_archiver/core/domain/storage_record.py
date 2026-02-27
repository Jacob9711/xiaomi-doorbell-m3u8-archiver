"""Storage result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .time_utils import utcnow


@dataclass(slots=True)
class StorageRecord:
    """Storage result record."""

    location: str
    stored_at: datetime = field(default_factory=utcnow)
    meta: dict[str, Any] = field(default_factory=dict)
