"""Sensor entities exposing runtime metrics."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant

from ..const import (
    DOMAIN,
    SENSOR_LAST_JOB_STATUS,
    SENSOR_QUEUE_FETCH,
    SENSOR_QUEUE_PROCESS,
    SENSOR_TOTAL_DONE,
    SENSOR_TOTAL_FAILED,
)
from .coordinator import IntegrationRuntime

SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities,
    discovery_info: dict | None = None,
) -> None:
    """Set up metric sensors via platform discovery."""
    runtime: IntegrationRuntime | None = hass.data.get(DOMAIN)
    if runtime is None:
        return

    async_add_entities(
        [
            RuntimeMetricSensor(runtime, SENSOR_TOTAL_DONE, "Total Done"),
            RuntimeMetricSensor(runtime, SENSOR_TOTAL_FAILED, "Total Failed"),
            RuntimeMetricSensor(runtime, SENSOR_QUEUE_FETCH, "Fetch Queue Size"),
            RuntimeMetricSensor(runtime, SENSOR_QUEUE_PROCESS, "Process Queue Size"),
            RuntimeMetricSensor(runtime, SENSOR_LAST_JOB_STATUS, "Last Job Status"),
        ],
        True,
    )


class RuntimeMetricSensor(SensorEntity):
    """Expose one runtime metric as a sensor."""

    _attr_should_poll = True

    def __init__(self, runtime: IntegrationRuntime, metric_key: str, name_suffix: str) -> None:
        self._runtime = runtime
        self._metric_key = metric_key
        self._attr_name = f"Xiaomi Doorbell M3U8 Archiver {name_suffix}"
        self._attr_unique_id = f"{DOMAIN}_{metric_key}"
        self._attr_native_value: Any = None

    @property
    def native_value(self) -> Any:
        return self._runtime.metrics().get(self._metric_key)
