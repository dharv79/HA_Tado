"""Temperature offset of a device."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .api import GENERATION_X
from .entity import TadoDeviceEntity, async_run

MIN_OFFSET = -10.0
MAX_OFFSET = 10.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add an offset control for each device that reports one (tado X)."""
    data = entry.runtime_data
    if data.generation != GENERATION_X:
        return
    async_add_entities(
        TadoTemperatureOffset(entry, serial)
        for serial, device in data.coordinator.devices.items()
        if device["temperature_offset"] is not None
    )


class TadoTemperatureOffset(TadoDeviceEntity, NumberEntity):
    """Temperature offset applied by a thermostat or sensor."""

    _attr_translation_key = "temperature_offset"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_OFFSET
    _attr_native_max_value = MAX_OFFSET
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX

    def __init__(self, entry: TadoResumeConfigEntry, serial: str) -> None:
        super().__init__(entry, serial, "temperature_offset")

    @property
    def native_value(self) -> float | None:
        device = self._device
        return device["temperature_offset"] if device else None

    async def async_set_native_value(self, value: float) -> None:
        """Write the offset to the device."""
        data = self._data
        await async_run(
            data,
            data.api.async_set_temperature_offset(
                data.home_id, data.generation, self._serial, round(value, 1)
            ),
            "Temperature offset change",
        )
