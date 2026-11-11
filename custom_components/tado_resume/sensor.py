"""Room, device and weather sensors."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .capabilities import CAP_HEATING_POWER, CAP_HUMIDITY
from .entity import (
    TadoDeviceEntity,
    TadoEntity,
    TadoRoomEntity,
    heating_power,
    home_device_info,
    number,
)

# Weather payload key -> (translation key, payload field, unit, device class)
WEATHER_SENSORS = {
    "outsideTemperature": (
        "outside_temperature",
        "celsius",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
    ),
    "solarIntensity": ("solar_intensity", "percentage", PERCENTAGE, None),
    "weatherState": ("weather_state", "value", None, None),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensors only where the data exists."""
    data = entry.runtime_data
    coordinator = data.coordinator
    entities: list[SensorEntity] = []
    for room in data.rooms:
        room_caps = coordinator.capabilities.get(room["id"], frozenset())
        if CAP_HEATING_POWER in room_caps:
            entities.append(TadoHeatingPower(entry, room["id"], room["name"]))
        if CAP_HUMIDITY in room_caps:
            entities.append(TadoHumidity(entry, room["id"], room["name"]))
    for serial, device in coordinator.devices.items():
        if device["firmware"]:
            entities.append(TadoFirmware(entry, serial))
    weather = (coordinator.data or {}).get("weather")
    if isinstance(weather, dict):
        entities.extend(TadoWeather(entry, key) for key in WEATHER_SENSORS if key in weather)
    async_add_entities(entities)


class TadoWeather(TadoEntity, SensorEntity):
    """Outside conditions reported by tado for the home location."""

    def __init__(self, entry: TadoResumeConfigEntry, key: str) -> None:
        super().__init__(entry)
        self._key = key
        translation, self._field, unit, device_class = WEATHER_SENSORS[key]
        self._attr_translation_key = translation
        self._attr_unique_id = f"{self._data.home_id}_weather_{key}"
        self._attr_device_info = home_device_info(self._data.home_id)
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if unit is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | str | None:
        item = (self._state.get("weather") or {}).get(self._key)
        if not isinstance(item, dict):
            return None
        value = item.get(self._field)
        if self._key == "weatherState":
            return str(value).lower() if value else None
        return number(value)


class TadoHeatingPower(TadoRoomEntity, SensorEntity):
    """Current heating power of a room."""

    _attr_translation_key = "heating_power"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, entry, room_id, room_name):
        super().__init__(entry, room_id, room_name, "heating_power")

    @property
    def native_value(self) -> float | None:
        return heating_power(self._room)


class TadoHumidity(TadoRoomEntity, SensorEntity):
    """Room humidity."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry, room_id, room_name):
        super().__init__(entry, room_id, room_name, "humidity")

    @property
    def native_value(self) -> float | None:
        humidity = (self._room.get("sensorDataPoints") or {}).get("humidity") or {}
        return number(humidity.get("percentage"))


class TadoFirmware(TadoDeviceEntity, SensorEntity):
    """Firmware version of a device."""

    _attr_translation_key = "firmware"

    def __init__(self, entry, serial):
        super().__init__(entry, serial, "firmware")

    @property
    def native_value(self) -> str | None:
        device = self._device
        return device["firmware"] if device else None
