"""Device binary sensors: low battery and connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TadoResumeConfigEntry
from .capabilities import CAP_OPEN_WINDOW
from .devices import parse_devices
from .sensor import _DeviceEntity, room_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add binary sensors only for devices that report the data."""
    entities: list[BinarySensorEntity] = []
    data = entry.runtime_data
    for room in data.rooms:
        if CAP_OPEN_WINDOW in data.coordinator.capabilities.get(room["id"], ()):
            entities.append(TadoOpenWindow(entry, room["id"], room["name"]))
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


class TadoOpenWindow(CoordinatorEntity, BinarySensorEntity):
    """Open window detected in a room."""

    _attr_has_entity_name = True
    _attr_name = "Open window"
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def __init__(self, entry, room_id, room_name):
        data = entry.runtime_data
        super().__init__(data.coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{data.home_id}_{room_id}_open_window"
        self._attr_device_info = room_device_info(data.home_id, room_id, room_name)

    @property
    def is_on(self) -> bool | None:
        room = (self.coordinator.data or {}).get("rooms", {}).get(self._room_id)
        if room is None:
            return None
        if "openWindowDetected" in room:
            return bool(room["openWindowDetected"])
        return bool(room.get("openWindow"))
