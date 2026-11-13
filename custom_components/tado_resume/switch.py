"""Child lock of a device."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .entity import TadoDeviceEntity, async_run


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a child lock switch for each device that reports one."""
    async_add_entities(
        TadoChildLock(entry, serial)
        for serial, device in entry.runtime_data.coordinator.devices.items()
        if device["child_lock"] is not None
    )


class TadoChildLock(TadoDeviceEntity, SwitchEntity):
    """Child lock of a thermostat."""

    _attr_translation_key = "child_lock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: TadoResumeConfigEntry, serial: str) -> None:
        super().__init__(entry, serial, "child_lock")

    @property
    def is_on(self) -> bool | None:
        device = self._device
        return device["child_lock"] if device else None

    async def _set(self, enabled: bool) -> None:
        data = self._data
        await async_run(
            data,
            data.api.async_set_child_lock(data.home_id, data.generation, self._serial, enabled),
            "Child lock change",
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the child lock."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the child lock."""
        await self._set(False)
