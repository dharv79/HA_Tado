"""Device trackers for mobile devices with location tracking enabled."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import BaseTrackerEntity
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .const import DOMAIN
from .entity import MANUFACTURER, TadoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a tracker per opted-in mobile device."""
    async_add_entities(
        TadoTracker(entry, device_id, device.get("name"))
        for device_id, device in entry.runtime_data.coordinator.mobiles.items()
    )


class TadoTracker(TadoEntity, BaseTrackerEntity):
    """Whether a mobile device is at home according to tado."""

    _attr_name = None

    def __init__(self, entry: TadoResumeConfigEntry, device_id: Any, name: str | None):
        super().__init__(entry)
        self._device_id = device_id
        key = f"{self._data.home_id}_mobile_{device_id}"
        self._attr_unique_id = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, key)},
            name=name or f"Mobile device {device_id}",
            manufacturer=MANUFACTURER,
        )

    @property
    def _device(self) -> dict[str, Any] | None:
        return self.coordinator.mobiles.get(self._device_id)

    @property
    def available(self) -> bool:
        return super().available and self._device is not None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def state(self) -> str:
        at_home = ((self._device or {}).get("location") or {}).get("atHome")
        return STATE_HOME if at_home else STATE_NOT_HOME
