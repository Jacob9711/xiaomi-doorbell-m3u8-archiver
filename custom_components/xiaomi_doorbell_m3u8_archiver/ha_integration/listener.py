"""Home Assistant entity-state listener adapter."""

from __future__ import annotations

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .coordinator import IntegrationRuntime
from .resolver import build_source_request


def async_setup_listener(
    hass: HomeAssistant,
    runtime: IntegrationRuntime,
    camera_entity_id: str,
):
    """Track doorbell camera updates and enqueue tasks."""

    async def _on_state_change(event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        request = build_source_request(
            entity_id=camera_entity_id,
            attributes=new_state.attributes,
            source_type="ha_event",
        )
        if request is None:
            return
        await runtime.enqueue_request(request)

    return async_track_state_change_event(hass, [camera_entity_id], _on_state_change)
