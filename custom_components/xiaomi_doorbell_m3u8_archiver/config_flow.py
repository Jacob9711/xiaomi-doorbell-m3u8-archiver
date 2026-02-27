"""Config flow for Xiaomi Doorbell M3U8 Archiver."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import (
    CONF_CAMERA_ENTITY_ID,
    CONF_FFMPEG_PATH,
    CONF_FETCH_CONCURRENCY,
    CONF_MAX_QUEUE_SIZE,
    CONF_PROCESS_CONCURRENCY,
    CONF_RETRY_BACKOFF_SEC,
    CONF_RETRY_LIMIT,
    CONF_STORAGE_ROOT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class XiaomiDoorbellM3U8ArchiverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xiaomi Doorbell M3U8 Archiver."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle initial user step."""
        try:
            if user_input is not None:
                _LOGGER.debug(
                    "Config flow submit for camera entity: %s",
                    user_input.get(CONF_CAMERA_ENTITY_ID),
                )
                await self.async_set_unique_id(user_input[CONF_CAMERA_ENTITY_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_CAMERA_ENTITY_ID],
                    data=user_input,
                )

            schema = vol.Schema(
                {
                    vol.Required(CONF_CAMERA_ENTITY_ID): selector.EntitySelector(),
                    vol.Optional(CONF_STORAGE_ROOT, default="/media/xiaomi_video"): cv.string,
                    vol.Optional(CONF_FFMPEG_PATH, default="ffmpeg"): cv.string,
                    vol.Optional(CONF_FETCH_CONCURRENCY, default=2): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=4, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(CONF_PROCESS_CONCURRENCY, default=1): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(CONF_MAX_QUEUE_SIZE, default=200): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, mode=selector.NumberSelectorMode.BOX)
                    ),
                    vol.Optional(CONF_RETRY_LIMIT, default=1): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, mode=selector.NumberSelectorMode.BOX)
                    ),
                    vol.Optional(CONF_RETRY_BACKOFF_SEC, default=0.2): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, step=0.1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)
        except Exception:
            _LOGGER.exception("Config flow step_user failed")
            raise
