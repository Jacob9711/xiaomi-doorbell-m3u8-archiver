from custom_components.xiaomi_doorbell_m3u8_archiver.ha_integration.runtime_routing import (
    resolve_runtime,
    resolve_status_runtimes,
)


def test_resolve_runtime_by_entry_id() -> None:
    # Intent: explicit entry_id must have highest routing priority.
    # Expect: runtime for that entry is returned.
    runtimes = {"e1": object(), "e2": object()}
    mapping = {"e1": "camera.a", "e2": "camera.b"}

    runtime = resolve_runtime(runtimes, mapping, entry_id="e2")
    assert runtime is runtimes["e2"]


def test_resolve_runtime_by_entity_id() -> None:
    # Intent: entity-based routing should resolve to its mapped entry.
    # Expect: matching entry runtime is returned.
    runtimes = {"e1": object(), "e2": object()}
    mapping = {"e1": "camera.a", "e2": "camera.b"}

    runtime = resolve_runtime(runtimes, mapping, entity_id="camera.a")
    assert runtime is runtimes["e1"]


def test_resolve_runtime_requires_target_for_multi_when_no_match() -> None:
    # Intent: avoid ambiguous cross-instance operations in multi-entry setup.
    # Expect: missing target raises ValueError instead of picking arbitrary runtime.
    runtimes = {"e1": object(), "e2": object()}
    mapping = {"e1": "camera.a", "e2": "camera.b"}

    try:
        resolve_runtime(runtimes, mapping)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Multiple runtimes configured" in str(exc)


def test_resolve_status_runtimes_returns_all_for_multi_without_target() -> None:
    # Intent: status endpoint supports aggregated fleet view.
    # Expect: all runtimes are returned when target is omitted.
    runtimes = {"e1": object(), "e2": object()}
    mapping = {"e1": "camera.a", "e2": "camera.b"}

    resolved = resolve_status_runtimes(runtimes, mapping)
    assert resolved == runtimes


def test_resolve_status_runtimes_returns_single_for_target() -> None:
    # Intent: targeted status query should not include unrelated entries.
    # Expect: only mapped runtime is returned.
    runtimes = {"e1": object(), "e2": object()}
    mapping = {"e1": "camera.a", "e2": "camera.b"}

    resolved = resolve_status_runtimes(runtimes, mapping, entity_id="camera.b")
    assert resolved == {"e2": runtimes["e2"]}
