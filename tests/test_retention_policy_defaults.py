from custom_components.xiaomi_doorbell_m3u8_archiver.core.policies import RetentionPolicy


def test_retention_policy_defaults() -> None:
    policy = RetentionPolicy()
    assert policy.active_keep_count == 30
    assert policy.retention_days == 3650
    assert policy.delete_enabled is False
