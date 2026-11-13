"""Home/Away presence select."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .api import PRESENCE_AUTO, PRESENCE_OPTIONS
from .entity import TadoEntity, async_run, home_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the presence select when the home reports presence."""
    presence = (entry.runtime_data.coordinator.data or {}).get("presence")
    if isinstance(presence, dict) and "presence" in presence:
        async_add_entities([TadoPresence(entry)])


class TadoPresence(TadoEntity, SelectEntity):
    """Home, away, or automatic (geofencing) presence."""

    _attr_translation_key = "presence"
    _attr_options = list(PRESENCE_OPTIONS)

    def __init__(self, entry: TadoResumeConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{self._data.home_id}_presence"
        self._attr_device_info = home_device_info(self._data.home_id)

    @property
    def _presence(self) -> dict[str, Any]:
        return self._state.get("presence") or {}

    @property
    def _effective(self) -> str:
        return str(self._presence.get("presence", "")).lower()

    @property
    def current_option(self) -> str | None:
        if not self._presence.get("presenceLocked"):
            return PRESENCE_AUTO
        return self._effective if self._effective in PRESENCE_OPTIONS else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Current effective presence (home or away), also while automatic."""
        return {"effective_presence": self._effective}

    async def async_select_option(self, option: str) -> None:
        """Change presence."""
        data = self._data
        if data.away:
            await data.away.async_cancel()
        await async_run(
            data,
            data.api.async_set_presence(data.home_id, data.generation, option),
            "Presence change",
        )
