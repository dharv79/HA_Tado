"""Resume-schedule buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TadoResumeConfigEntry
from .api import TadoError
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
