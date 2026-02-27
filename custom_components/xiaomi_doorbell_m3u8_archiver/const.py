"""Constants for Xiaomi Doorbell M3U8 Archiver integration."""

DOMAIN = "xiaomi_doorbell_m3u8_archiver"

CONF_NAME_DEFAULT = "Xiaomi Doorbell M3U8 Archiver"
CONF_CAMERA_ENTITY_ID = "camera_entity_id"
CONF_FETCH_CONCURRENCY = "fetch_concurrency"
CONF_PROCESS_CONCURRENCY = "process_concurrency"
CONF_MAX_QUEUE_SIZE = "max_queue_size"
CONF_RETRY_LIMIT = "retry_limit"
CONF_RETRY_BACKOFF_SEC = "retry_backoff_sec"
CONF_STORAGE_ROOT = "storage_root"
CONF_FFMPEG_PATH = "ffmpeg_path"

SERVICE_ENQUEUE = "enqueue"
SERVICE_GET_STATUS = "get_status"

ATTR_ENTITY_ID = "entity_id"
ATTR_EVENT_TIME = "event_time"
ATTR_ENTRY_ID = "entry_id"

META_STREAM_URL = "stream_url"
META_MOTION_VIDEO_TIME = "motion_video_time"

SENSOR_TOTAL_DONE = "total_done"
SENSOR_TOTAL_FAILED = "total_failed"
SENSOR_QUEUE_FETCH = "queue_fetch_size"
SENSOR_QUEUE_PROCESS = "queue_process_size"
SENSOR_LAST_JOB_STATUS = "last_job_status"
SENSOR_CURRENT_JOB_STATUS = "current_job_status"
SENSOR_PROCESSED_TODAY = "processed_today"
SENSOR_IS_BUSY = "is_busy"
