"""Retention policy model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RetentionPolicy:
    """Storage retention behavior.

    The policy combines two knobs intentionally: keep newest N files regardless of
    age, then apply age-based cleanup for the rest.
    """

    active_keep_count: int = 30
    retention_days: int = 3650
    delete_enabled: bool = False
