"""Home Assistant service registration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from ..const import (
    ATTR_ENTITY_ID,
    ATTR_EVENT_TIME,
    DOMAIN,
    SERVICE_ENQUEUE,
    SERVICE_RUN_ARCHIVE_MAINTENANCE,
)
from .coordinator import IntegrationRuntime
from .resolver import build_source_request

ENQUEUE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_EVENT_TIME): cv.string,
    }
)


def async_register_services(hass: HomeAssistant, runtime: IntegrationRuntime) -> None:
    """Register integration services."""

    async def _handle_enqueue(call: ServiceCall) -> None:
        entity_id = call.data[ATTR_ENTITY_ID]
        state = hass.states.get(entity_id)
        if state is None:
            raise ValueError(f"Entity not found: {entity_id}")

        request = build_source_request(
            entity_id=entity_id,
            attributes=state.attributes,
            source_type="manual",
            event_time=call.data.get(ATTR_EVENT_TIME),
        )
        if request is None:
            raise ValueError(f"Entity has no stream_address attribute: {entity_id}")

        await runtime.enqueue_request(request)

    async def _handle_archive_maintenance(_: ServiceCall) -> None:
        await runtime.archive.apply_policy(runtime.orchestrator.archive_policy)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENQUEUE,
        _handle_enqueue,
        schema=ENQUEUE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_ARCHIVE_MAINTENANCE,
        _handle_archive_maintenance,
    )
