"""Home/Away presence select."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TadoResumeConfigEntry
from .api import PRESENCE_AUTO, PRESENCE_OPTIONS, TadoError
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the presence select when the home reports presence."""
    presence = (entry.runtime_data.coordinator.data or {}).get("presence")
    if isinstance(presence, dict) and "presence" in presence:
        async_add_entities([TadoPresence(entry)])


class TadoPresence(CoordinatorEntity, SelectEntity):
    """Home, away, or automatic (geofencing) presence."""

    _attr_has_entity_name = True
    _attr_translation_key = "presence"
    _attr_options = list(PRESENCE_OPTIONS)

    def __init__(self, entry: TadoResumeConfigEntry) -> None:
        data = entry.runtime_data
        super().__init__(data.coordinator)
        self._entry = entry
        self._attr_unique_id = f"{data.home_id}_presence"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{data.home_id}_home")},
            name="Tado home",
            manufacturer="tado°",
        )

    @property
    def current_option(self) -> str | None:
        presence = (self.coordinator.data or {}).get("presence") or {}
        if not presence.get("presenceLocked"):
            return PRESENCE_AUTO
        value = str(presence.get("presence", "")).lower()
        return value if value in PRESENCE_OPTIONS else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Current effective presence (home or away), also while automatic."""
        presence = (self.coordinator.data or {}).get("presence") or {}
        return {"effective_presence": str(presence.get("presence", "")).lower()}

    async def async_select_option(self, option: str) -> None:
        """Change presence."""
        data = self._entry.runtime_data
        try:
            await data.api.async_set_presence(data.home_id, data.generation, option)
        except TadoError as err:
            raise HomeAssistantError(f"Presence change failed: {err}") from err
        await data.coordinator.async_request_refresh()
