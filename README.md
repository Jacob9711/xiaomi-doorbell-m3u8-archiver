## Xiaomi Doorbell M3U8 Archiver

Custom Home Assistant integration for Xiaomi doorbell video event pipeline.

### Install

1. Copy `custom_components/xiaomi_doorbell_m3u8_archiver` into your HA config directory.
2. Restart Home Assistant.

### Configuration

Add to `configuration.yaml`:

```yaml
xiaomi_doorbell_m3u8_archiver:
  camera_entity_id: camera.loock_r2_559c_video_doorbell
  archive_root: /media/xiaomi_video
  ffmpeg_path: ffmpeg
  fetch_concurrency: 2
  process_concurrency: 1
  max_queue_size: 200
  dedup_window_sec: 60
  retry_limit: 1
  retry_backoff_sec: 0.2
```

`camera_entity_id` is optional. If omitted, only manual service enqueue is active.

### Services

- `xiaomi_doorbell_m3u8_archiver.enqueue`
- `xiaomi_doorbell_m3u8_archiver.run_archive_maintenance`

`enqueue` service parameters:

- `entity_id` (required): camera or doorbell entity id
- `event_time` (optional): manual event timestamp override

Users do not need to configure or provide `stream_url`. The integration resolves stream metadata from the configured entity state.

`archive_root` and `ffmpeg_path` are optional and use defaults shown above.

### Sensors

- `sensor.xiaomi_doorbell_m3u8_archiver_total_done`
- `sensor.xiaomi_doorbell_m3u8_archiver_total_failed`
- `sensor.xiaomi_doorbell_m3u8_archiver_queue_fetch_size`
- `sensor.xiaomi_doorbell_m3u8_archiver_queue_process_size`
- `sensor.xiaomi_doorbell_m3u8_archiver_last_job_status`
