"""Device trackers for mobile devices with location tracking enabled."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import BaseTrackerEntity
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TadoResumeConfigEntry
from .const import DOMAIN


def tracked_devices(raw: Any) -> dict[Any, dict[str, Any]]:
    """Return {id: device} for mobile devices that share their location."""
    result: dict[Any, dict[str, Any]] = {}
    for item in raw if isinstance(raw, list) else []:
        settings = item.get("settings") or {}
        if item.get("id") is not None and settings.get("geoTrackingEnabled"):
            result[item["id"]] = item
    return result


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a tracker per opted-in mobile device."""
    raw = (entry.runtime_data.coordinator.data or {}).get("mobile_devices")
    async_add_entities(
        TadoTracker(entry, device_id, device.get("name"))
        for device_id, device in tracked_devices(raw).items()
    )


class TadoTracker(CoordinatorEntity, BaseTrackerEntity):
    """Whether a mobile device is at home according to tado."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: TadoResumeConfigEntry, device_id: Any, name: str | None):
        data = entry.runtime_data
        super().__init__(data.coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{data.home_id}_mobile_{device_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{data.home_id}_mobile_{device_id}")},
            name=name or f"Mobile device {device_id}",
            manufacturer="tado°",
        )

    @property
    def _device(self) -> dict[str, Any] | None:
        raw = (self.coordinator.data or {}).get("mobile_devices")
        return tracked_devices(raw).get(self._device_id)

    @property
    def available(self) -> bool:
        return super().available and self._device is not None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def state(self) -> str:
        device = self._device or {}
        at_home = (device.get("location") or {}).get("atHome")
        return STATE_HOME if at_home else STATE_NOT_HOME
