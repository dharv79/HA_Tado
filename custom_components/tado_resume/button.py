"""Resume-schedule buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .api import GENERATION_X, TadoError
from .capabilities import CAP_OPEN_WINDOW
from .const import DOMAIN, SERVICE_RESUME_SCHEDULE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a resume button per room plus a whole-home button."""
    data = entry.runtime_data
    entities: list[ButtonEntity] = [
        TadoResumeButton(entry, room["id"], room["name"]) for room in data.rooms
    ]
    entities.append(TadoResumeButton(entry, None, None))
    entities.append(TadoHomeActionButton(entry, "turn_off_all", "async_turn_off_all"))
    if data.generation == GENERATION_X:
        entities.append(TadoHomeActionButton(entry, "boost_all", "async_boost_all"))
    for room in data.rooms:
        if CAP_OPEN_WINDOW in data.coordinator.capabilities.get(room["id"], ()):
            for active in (True, False):
                entities.append(
                    TadoOpenWindowButton(entry, room["id"], room["name"], active)
                )
    async_add_entities(entities)

    entity_platform.async_get_current_platform().async_register_entity_service(
        SERVICE_RESUME_SCHEDULE, None, "async_press"
    )


class TadoResumeButton(ButtonEntity):
    """Resume the schedule for one room, or the whole home when room is None."""

    _attr_has_entity_name = True
    _attr_translation_key = "resume_schedule"

    def __init__(
        self, entry: TadoResumeConfigEntry, room_id: int | None, room_name: str | None
    ) -> None:
        self._entry = entry
        self._room_id = room_id
        data = entry.runtime_data
        scope = "home" if room_id is None else str(room_id)
        self._attr_unique_id = f"{data.home_id}_{scope}_resume_schedule"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{data.home_id}_{scope}")},
            name="Tado home" if room_id is None else room_name,
            manufacturer="tado°",
        )

    async def async_press(self) -> None:
        """Resume the schedule."""
        data = self._entry.runtime_data
        try:
            if self._room_id is None:
                await data.api.async_resume_all(
                    data.home_id, data.generation, [r["id"] for r in data.rooms]
                )
            else:
                await data.api.async_resume_room(
                    data.home_id, data.generation, self._room_id
                )
        except TadoError as err:
            raise HomeAssistantError(f"Resume failed: {err}") from err
        await data.coordinator.async_request_refresh()


class TadoOpenWindowButton(ButtonEntity):
    """Activate or cancel open-window mode for a room."""

    _attr_has_entity_name = True

    def __init__(
        self, entry: TadoResumeConfigEntry, room_id: int, room_name: str, active: bool
    ) -> None:
        self._entry = entry
        self._room_id = room_id
        self._active = active
        data = entry.runtime_data
        key = "open_window_activate" if active else "open_window_reset"
        self._attr_translation_key = key
        self._attr_unique_id = f"{data.home_id}_{room_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{data.home_id}_{room_id}")},
            name=room_name,
            manufacturer="tado°",
        )

    async def async_press(self) -> None:
        """Send the open-window command."""
        data = self._entry.runtime_data
        try:
            await data.api.async_set_open_window(
                data.home_id, data.generation, self._room_id, self._active
            )
        except TadoError as err:
            raise HomeAssistantError(f"Open window request failed: {err}") from err
        await data.coordinator.async_request_refresh()


class TadoHomeActionButton(ButtonEntity):
    """Whole-home quick action."""

    _attr_has_entity_name = True

    def __init__(self, entry: TadoResumeConfigEntry, key: str, method: str) -> None:
        self._entry = entry
        self._method = method
        data = entry.runtime_data
        self._attr_translation_key = key
        self._attr_unique_id = f"{data.home_id}_home_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{data.home_id}_home")},
            name="Tado home",
            manufacturer="tado°",
        )

    async def async_press(self) -> None:
        """Run the quick action."""
        data = self._entry.runtime_data
        try:
            await getattr(data.api, self._method)(
                data.home_id, data.generation, [r["id"] for r in data.rooms]
            )
        except TadoError as err:
            raise HomeAssistantError(f"Quick action failed: {err}") from err
        await data.coordinator.async_request_refresh()
