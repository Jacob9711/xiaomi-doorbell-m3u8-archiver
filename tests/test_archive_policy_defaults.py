from custom_components.xiaomi_doorbell_m3u8_archiver.core.policies import ArchivePolicy


def test_archive_policy_defaults() -> None:
    policy = ArchivePolicy()
    assert policy.active_keep_count == 30
    assert policy.retention_days == 3650
    assert policy.delete_enabled is False
