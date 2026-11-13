"""Resume-schedule and whole-home action buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .api import GENERATION_X
from .const import SERVICE_RESUME_SCHEDULE
from .entity import async_run, home_device_info, room_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a resume button per room plus the whole-home buttons."""
    data = entry.runtime_data
    entities: list[ButtonEntity] = [
        TadoResumeButton(entry, room["id"], room["name"]) for room in data.rooms
    ]
    entities.append(TadoResumeButton(entry, None, None))
    entities.append(TadoHomeActionButton(entry, "turn_off_all", "async_turn_off_all"))
    if data.generation == GENERATION_X:
        entities.append(TadoHomeActionButton(entry, "boost_all", "async_boost_all"))
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
        self._data = data = entry.runtime_data
        self._room_id = room_id
        scope = "home" if room_id is None else str(room_id)
        self._attr_unique_id = f"{data.home_id}_{scope}_resume_schedule"
        self._attr_device_info = (
            home_device_info(data.home_id)
            if room_id is None
            else room_device_info(data.home_id, room_id, room_name)
        )

    async def async_press(self) -> None:
        """Resume the schedule."""
        data = self._data
        if self._room_id is None:
            request = data.api.async_resume_all(data.home_id, data.generation, data.room_ids)
        else:
            request = data.api.async_resume_room(data.home_id, data.generation, self._room_id)
        await async_run(data, request, "Resume")


class TadoHomeActionButton(ButtonEntity):
    """Whole-home quick action."""

    _attr_has_entity_name = True

    def __init__(self, entry: TadoResumeConfigEntry, key: str, method: str) -> None:
        self._data = data = entry.runtime_data
        self._method = method
        self._attr_translation_key = key
        self._attr_unique_id = f"{data.home_id}_home_{key}"
        self._attr_device_info = home_device_info(data.home_id)

    async def async_press(self) -> None:
        """Run the quick action."""
        data = self._data
        request = getattr(data.api, self._method)(data.home_id, data.generation, data.room_ids)
        await async_run(data, request, "Quick action")
