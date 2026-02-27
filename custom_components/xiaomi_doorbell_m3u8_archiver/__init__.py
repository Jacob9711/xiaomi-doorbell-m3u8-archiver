"""Home Assistant integration bootstrap."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .const import (
    CONF_ARCHIVE_ROOT,
    CONF_CAMERA_ENTITY_ID,
    CONF_DEDUP_WINDOW_SEC,
    CONF_FFMPEG_PATH,
    CONF_FETCH_CONCURRENCY,
    CONF_MAX_QUEUE_SIZE,
    CONF_NAME_DEFAULT,
    CONF_PROCESS_CONCURRENCY,
    CONF_RETRY_LIMIT,
    CONF_RETRY_BACKOFF_SEC,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

CONF_NAME = "name"
EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
async_load_platform = None

try:
    import voluptuous as vol
    from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP
    from homeassistant.helpers import config_validation as cv
    from homeassistant.helpers.discovery import async_load_platform

    CONFIG_SCHEMA = vol.Schema(
        {
            DOMAIN: vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=CONF_NAME_DEFAULT): cv.string,
                    vol.Optional(CONF_CAMERA_ENTITY_ID): cv.entity_id,
                    vol.Optional(CONF_FETCH_CONCURRENCY, default=2): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=4)
                    ),
                    vol.Optional(CONF_PROCESS_CONCURRENCY, default=1): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=1)
                    ),
                    vol.Optional(CONF_MAX_QUEUE_SIZE, default=200): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    ),
                    vol.Optional(CONF_DEDUP_WINDOW_SEC, default=60): vol.All(
                        vol.Coerce(int), vol.Range(min=0)
                    ),
                    vol.Optional(CONF_RETRY_LIMIT, default=1): vol.All(
                        vol.Coerce(int), vol.Range(min=0)
                    ),
                    vol.Optional(CONF_RETRY_BACKOFF_SEC, default=0.2): vol.All(
                        vol.Coerce(float), vol.Range(min=0)
                    ),
                    vol.Optional(CONF_ARCHIVE_ROOT, default="/media/xiaomi_video"): cv.string,
                    vol.Optional(CONF_FFMPEG_PATH, default="ffmpeg"): cv.string,
                }
            )
        },
        extra=vol.ALLOW_EXTRA,
    )
except ModuleNotFoundError:
    CONFIG_SCHEMA = None


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration from YAML."""
    if CONFIG_SCHEMA is None or async_load_platform is None:
        raise RuntimeError("Home Assistant runtime dependencies are not available")

    from .ha_integration.coordinator import IntegrationRuntime
    from .ha_integration.listener import async_setup_listener
    from .ha_integration.services import async_register_services

    cfg = config.get(DOMAIN)
    if cfg is None:
        return True

    runtime = IntegrationRuntime.from_config(cfg)
    hass.data[DOMAIN] = runtime

    await runtime.start()
    async_register_services(hass, runtime)

    camera_entity_id = cfg.get(CONF_CAMERA_ENTITY_ID)
    if camera_entity_id:
        runtime.unsub_listener = async_setup_listener(hass, runtime, camera_entity_id)
        _LOGGER.info("Listening Xiaomi doorbell entity: %s", camera_entity_id)
    else:
        _LOGGER.warning(
            "No %s configured; only manual service enqueue is active",
            CONF_CAMERA_ENTITY_ID,
        )

    await async_load_platform(hass, "sensor", DOMAIN, {}, config)

    async def _stop_runtime(_: object) -> None:
        await runtime.stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop_runtime)
    _LOGGER.info("%s setup complete", DOMAIN)
    return True
