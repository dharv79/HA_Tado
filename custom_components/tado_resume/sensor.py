"""Room and device sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TadoResumeConfigEntry
from .capabilities import CAP_HEATING_POWER, CAP_HUMIDITY
from .const import DOMAIN
from .devices import parse_devices


def room_device_info(home_id: int, room_id: int, name: str | None = None) -> DeviceInfo:
    """Device registry entry shared by all entities of a room."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{home_id}_{room_id}")},
        name=name,
        manufacturer="tado°",
    )


def device_info(home_id: int, device: dict[str, Any]) -> DeviceInfo:
    """Device registry entry for a physical tado device."""
    info = DeviceInfo(
        identifiers={(DOMAIN, device["serial"])},
        name=f"tado {device['type'] or 'device'} {device['serial']}",
        manufacturer="tado°",
        model=device["type"],
        sw_version=device["firmware"],
    )
    if device["room_id"] is not None:
        info["via_device"] = (DOMAIN, f"{home_id}_{device['room_id']}")
    return info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensors only where the data exists."""
    data = entry.runtime_data
    caps = data.coordinator.capabilities
    entities: list[SensorEntity] = []
    for room in data.rooms:
        room_caps = caps.get(room["id"], frozenset())
        if CAP_HEATING_POWER in room_caps:
            entities.append(TadoHeatingPower(entry, room["id"], room["name"]))
        if CAP_HUMIDITY in room_caps:
            entities.append(TadoHumidity(entry, room["id"], room["name"]))
    for device in parse_devices((data.coordinator.data or {}).get("devices")):
        if device["firmware"]:
            entities.append(TadoFirmware(entry, device["serial"]))
    async_add_entities(entities)


class _RoomSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: TadoResumeConfigEntry, room_id: int, room_name: str, key: str):
        data = entry.runtime_data
        super().__init__(data.coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{data.home_id}_{room_id}_{key}"
        self._attr_device_info = room_device_info(data.home_id, room_id, room_name)

    @property
    def _room(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("rooms", {}).get(self._room_id, {})

    @property
    def available(self) -> bool:
        return super().available and bool(self._room)


class TadoHeatingPower(_RoomSensor):
    """Current heating power of a room."""

    _attr_translation_key = "heating_power"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, entry, room_id, room_name):
        super().__init__(entry, room_id, room_name, "heating_power")

    @property
    def native_value(self) -> float | None:
        power = self._room.get("heatingPower")
        if power is None:
            power = (self._room.get("activityDataPoints") or {}).get("heatingPower")
        value = (power or {}).get("percentage")
        return float(value) if isinstance(value, (int, float)) else None


class TadoHumidity(_RoomSensor):
    """Room humidity."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry, room_id, room_name):
        super().__init__(entry, room_id, room_name, "humidity")

    @property
    def native_value(self) -> float | None:
        humidity = (self._room.get("sensorDataPoints") or {}).get("humidity") or {}
        value = humidity.get("percentage")
        return float(value) if isinstance(value, (int, float)) else None


class _DeviceEntity(CoordinatorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: TadoResumeConfigEntry, serial: str, key: str):
        data = entry.runtime_data
        super().__init__(data.coordinator)
        self._home_id = data.home_id
        self._serial = serial
        self._attr_unique_id = f"{data.home_id}_{serial}_{key}"
        device = self._device or {"serial": serial, "type": None, "room_id": None, "firmware": None}
        self._attr_device_info = device_info(data.home_id, device)

    @property
    def _device(self) -> dict[str, Any] | None:
        for device in parse_devices((self.coordinator.data or {}).get("devices")):
            if device["serial"] == self._serial:
                return device
        return None

    @property
    def available(self) -> bool:
        return super().available and self._device is not None


class TadoFirmware(_DeviceEntity, SensorEntity):
    """Firmware version of a device."""

    _attr_translation_key = "firmware"

    def __init__(self, entry, serial):
        super().__init__(entry, serial, "firmware")

    @property
    def native_value(self) -> str | None:
        device = self._device
        return device["firmware"] if device else None
