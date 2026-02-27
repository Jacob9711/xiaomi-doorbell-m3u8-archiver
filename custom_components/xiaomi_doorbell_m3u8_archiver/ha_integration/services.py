"""Home Assistant service registration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from ..const import (
    ATTR_ENTRY_ID,
    ATTR_ENTITY_ID,
    ATTR_EVENT_TIME,
    DOMAIN,
    SERVICE_ENQUEUE,
    SERVICE_GET_STATUS,
)
from .runtime_routing import resolve_runtime, resolve_status_runtimes
from .resolver import build_source_request

ENQUEUE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_EVENT_TIME): cv.string,
    }
)

TARGET_SCHEMA = vol.Schema(
    {
        vol.Exclusive(ATTR_ENTRY_ID, "target"): cv.string,
        vol.Exclusive(ATTR_ENTITY_ID, "target"): cv.entity_id,
    }
)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""

    domain_data = hass.data.setdefault(
        DOMAIN,
        {"runtimes": {}, "entry_camera_entity": {}, "services_registered": False},
    )
    if domain_data.get("services_registered"):
        return

    def _get_runtime(
        *,
        entry_id: str | None = None,
        entity_id: str | None = None,
    ):
        runtimes = domain_data.get("runtimes", {})
        entry_camera_entity = domain_data.get("entry_camera_entity", {})
        return resolve_runtime(
            runtimes,
            entry_camera_entity,
            entry_id=entry_id,
            entity_id=entity_id,
        )

    def _get_status_runtimes(
        *,
        entry_id: str | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        runtimes = domain_data.get("runtimes", {})
        entry_camera_entity = domain_data.get("entry_camera_entity", {})
        return resolve_status_runtimes(
            runtimes,
            entry_camera_entity,
            entry_id=entry_id,
            entity_id=entity_id,
        )

    async def _handle_enqueue(call: ServiceCall) -> None:
        entity_id = call.data[ATTR_ENTITY_ID]
        runtime = _get_runtime(entity_id=entity_id)
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

    async def _handle_get_status(call: ServiceCall) -> dict:
        entry_id = call.data.get(ATTR_ENTRY_ID)
        entity_id = call.data.get(ATTR_ENTITY_ID)
        target_runtimes = _get_status_runtimes(entry_id=entry_id, entity_id=entity_id)

        entry_camera_entity = domain_data.get("entry_camera_entity", {})
        instances: dict[str, dict] = {}
        total_done = 0
        total_failed = 0
        processed_today = 0
        busy_instances = 0

        for target_entry_id, runtime in target_runtimes.items():
            metrics = runtime.metrics()
            metrics_with_entity = {
                **metrics,
                "camera_entity_id": entry_camera_entity.get(target_entry_id),
            }
            instances[target_entry_id] = metrics_with_entity
            total_done += int(metrics.get("total_done", 0))
            total_failed += int(metrics.get("total_failed", 0))
            processed_today += int(metrics.get("processed_today", 0))
            if metrics.get("current_job_status") == "busy":
                busy_instances += 1

        if len(instances) == 1:
            only_entry_id = next(iter(instances))
            return {
                "mode": "single",
                "entry_id": only_entry_id,
                **instances[only_entry_id],
            }

        # Multi-instance aggregate keeps automation callers from needing separate
        # service round-trips just to compute fleet-level health.
        return {
            "mode": "multi",
            "instances": instances,
            "summary": {
                "total_done": total_done,
                "total_failed": total_failed,
                "processed_today": processed_today,
                "busy_instances": busy_instances,
            },
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENQUEUE,
        _handle_enqueue,
        schema=ENQUEUE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_STATUS,
        _handle_get_status,
        schema=TARGET_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    domain_data["services_registered"] = True


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister integration services when no runtime remains."""
    for service_name in (SERVICE_ENQUEUE, SERVICE_GET_STATUS):
        if hass.services.has_service(DOMAIN, service_name):
            hass.services.async_remove(DOMAIN, service_name)

    domain_data = hass.data.setdefault(
        DOMAIN,
        {"runtimes": {}, "entry_camera_entity": {}, "services_registered": False},
    )
    domain_data["services_registered"] = False
