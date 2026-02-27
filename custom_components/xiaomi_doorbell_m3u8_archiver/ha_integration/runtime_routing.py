"""Runtime routing helpers for multi-entry service calls."""

from __future__ import annotations

from typing import Any


def resolve_runtime(
    runtimes: dict[str, Any],
    entry_camera_entity: dict[str, str],
    *,
    entry_id: str | None = None,
    entity_id: str | None = None,
) -> Any:
    """Resolve one runtime by explicit target or single-runtime fallback.

    Routing is strict for multi-entry setups to prevent silent cross-camera actions.
    """
    if not runtimes:
        raise ValueError("No runtime available")

    if entry_id and entity_id:
        mapped = entry_camera_entity.get(entry_id)
        if mapped != entity_id:
            raise ValueError(
                f"entry_id {entry_id} does not match entity_id {entity_id}"
            )

    if entry_id:
        runtime = runtimes.get(entry_id)
        if runtime is None:
            raise ValueError(f"Unknown entry_id: {entry_id}")
        return runtime

    if entity_id:
        matched_entries = [
            eid
            for eid, mapped_entity in entry_camera_entity.items()
            if mapped_entity == entity_id and eid in runtimes
        ]
        if len(matched_entries) == 1:
            return runtimes[matched_entries[0]]
        if len(matched_entries) > 1:
            raise ValueError(
                f"Entity {entity_id} maps to multiple entries; use entry_id"
            )
        if len(runtimes) == 1:
            return next(iter(runtimes.values()))
        raise ValueError(f"No runtime configured for entity_id: {entity_id}")

    if len(runtimes) == 1:
        return next(iter(runtimes.values()))

    raise ValueError("Multiple runtimes configured; specify entry_id or entity_id")


def resolve_status_runtimes(
    runtimes: dict[str, Any],
    entry_camera_entity: dict[str, str],
    *,
    entry_id: str | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """Resolve status targets, returning one or all runtimes.

    Status calls may intentionally aggregate all runtimes when target is omitted.
    """
    if entry_id or entity_id:
        runtime = resolve_runtime(
            runtimes,
            entry_camera_entity,
            entry_id=entry_id,
            entity_id=entity_id,
        )
        if entry_id:
            return {entry_id: runtime}

        for eid, mapped_entity in entry_camera_entity.items():
            if mapped_entity == entity_id and eid in runtimes:
                return {eid: runtimes[eid]}

        if len(runtimes) == 1:
            only_entry_id, only_runtime = next(iter(runtimes.items()))
            return {only_entry_id: only_runtime}

        raise ValueError(f"No runtime configured for entity_id: {entity_id}")

    if not runtimes:
        raise ValueError("No runtime available")

    if len(runtimes) == 1:
        only_entry_id, only_runtime = next(iter(runtimes.items()))
        return {only_entry_id: only_runtime}

    return dict(runtimes)
