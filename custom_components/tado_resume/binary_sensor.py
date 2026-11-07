"""Device binary sensors: low battery and connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .devices import parse_devices
from .sensor import _DeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add binary sensors only for devices that report the data."""
    entities: list[BinarySensorEntity] = []
    for device in parse_devices((entry.runtime_data.coordinator.data or {}).get("devices")):
        if device["battery_low"] is not None:
            entities.append(TadoLowBattery(entry, device["serial"]))
        if device["connected"] is not None:
            entities.append(TadoConnectivity(entry, device["serial"]))
    async_add_entities(entities)


class TadoLowBattery(_DeviceEntity, BinarySensorEntity):
    """Battery low indicator."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, entry, serial):
        super().__init__(entry, serial, "low_battery")

    @property
    def is_on(self) -> bool | None:
        device = self._device
        return device["battery_low"] if device else None


class TadoConnectivity(_DeviceEntity, BinarySensorEntity):
    """Connection state of a device."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, entry, serial):
        super().__init__(entry, serial, "connectivity")

    @property
    def is_on(self) -> bool | None:
        device = self._device
        return device["connected"] if device else None

