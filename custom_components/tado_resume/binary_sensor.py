"""Binary sensors: low battery, connectivity and open window."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .capabilities import CAP_OPEN_WINDOW
from .entity import TadoDeviceEntity, TadoRoomEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add binary sensors only where the data exists."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BinarySensorEntity] = []
    for room in entry.runtime_data.rooms:
        if CAP_OPEN_WINDOW in coordinator.capabilities.get(room["id"], ()):
            entities.append(TadoOpenWindow(entry, room["id"], room["name"]))
    for serial, device in coordinator.devices.items():
        if device["battery_low"] is not None:
            entities.append(TadoDeviceBinarySensor(entry, serial, "low_battery"))
        if device["connected"] is not None:
            entities.append(TadoDeviceBinarySensor(entry, serial, "connectivity"))
    async_add_entities(entities)


# unique-ID key -> (device class, field of the parsed device)
DEVICE_SENSORS = {
    "low_battery": (BinarySensorDeviceClass.BATTERY, "battery_low"),
    "connectivity": (BinarySensorDeviceClass.CONNECTIVITY, "connected"),
}


class TadoDeviceBinarySensor(TadoDeviceEntity, BinarySensorEntity):
    """Battery-low or connectivity state of a device."""

    def __init__(self, entry: TadoResumeConfigEntry, serial: str, key: str) -> None:
        super().__init__(entry, serial, key)
        self._attr_device_class, self._field = DEVICE_SENSORS[key]

    @property
    def is_on(self) -> bool | None:
        device = self._device
        return device[self._field] if device else None


class TadoOpenWindow(TadoRoomEntity, BinarySensorEntity):
    """Open window detected in a room."""

    _attr_name = "Open window"
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def __init__(self, entry: TadoResumeConfigEntry, room_id: int, room_name: str):
        super().__init__(entry, room_id, room_name, "open_window")

    @property
    def is_on(self) -> bool | None:
        room = self._room
        if not room:
            return None
        if "openWindowDetected" in room:
            return bool(room["openWindowDetected"])
        return bool(room.get("openWindow"))
