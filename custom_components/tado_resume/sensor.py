"""Room, device and weather sensors."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TadoResumeConfigEntry
from .capabilities import CAP_HEATING_POWER, CAP_HUMIDITY, CAP_OVERRIDE
from .entity import (
    TadoDeviceEntity,
    TadoEntity,
    TadoRoomEntity,
    heating_power,
    home_device_info,
    number,
    override_termination,
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
        if CAP_OVERRIDE in room_caps:
            entities.append(TadoOverrideEnds(entry, room["id"], room["name"]))
            entities.append(TadoOverrideRemaining(entry, room["id"], room["name"]))
    for serial, device in coordinator.devices.items():
        if device["firmware"]:
            entities.append(TadoFirmware(entry, serial))
    weather = (coordinator.data or {}).get("weather")
    if isinstance(weather, dict):
        entities.extend(TadoWeather(entry, key) for key in WEATHER_SENSORS if key in weather)
    entities.append(TadoLastUpdate(entry))
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


class TadoOverrideEnds(TadoRoomEntity, SensorEntity):
    """When the current manual override ends (unknown for manual or none)."""

    _attr_translation_key = "override_ends"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry, room_id, room_name):
        super().__init__(entry, room_id, room_name, "override_ends")

    @property
    def native_value(self) -> datetime | None:
        info = override_termination(self._room)
        if not info:
            return None
        if info["expiry"]:
            parsed = dt_util.parse_datetime(info["expiry"])
            if parsed is not None:
                return (
                    dt_util.as_utc(parsed) if parsed.tzinfo else parsed.replace(tzinfo=dt_util.UTC)
                )
        base = self.coordinator.last_success
        if info["remaining"] is not None and base is not None:
            return base + timedelta(seconds=info["remaining"])
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        info = override_termination(self._room)
        return {"termination": info["type"] if info else None}


class TadoOverrideRemaining(TadoRoomEntity, SensorEntity):
    """Seconds left of the current manual override."""

    _attr_translation_key = "override_remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, entry, room_id, room_name):
        super().__init__(entry, room_id, room_name, "override_remaining")

    @property
    def native_value(self) -> int | None:
        info = override_termination(self._room)
        return info["remaining"] if info else None


class TadoFirmware(TadoDeviceEntity, SensorEntity):
    """Firmware version of a device."""

    _attr_translation_key = "firmware"

    def __init__(self, entry, serial):
        super().__init__(entry, serial, "firmware")

    @property
    def native_value(self) -> str | None:
        device = self._device
        return device["firmware"] if device else None


class TadoLastUpdate(TadoEntity, SensorEntity):
    """When tado was last read successfully."""

    _attr_translation_key = "last_update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: TadoResumeConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{self._data.home_id}_last_update"
        self._attr_device_info = home_device_info(self._data.home_id)

    @property
    def available(self) -> bool:
        # Stay available while the API is failing: that is when it is useful.
        return True

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_success
