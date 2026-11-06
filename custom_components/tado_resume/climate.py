"""Climate entity per room."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    PRESET_BOOST,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import voluptuous as vol

from . import TadoResumeConfigEntry
from .api import (
    GENERATION_X,
    TERMINATION_NEXT_BLOCK,
    TERMINATION_TIMER,
    TERMINATIONS,
    TadoError,
)
from .capabilities import CAP_TARGET
from .const import DOMAIN, SERVICE_SET_ROOM_TEMPERATURE

PRESET_SCHEDULE = "schedule"
MIN_TEMP = 5.0
MAX_TEMP = 25.0
DEFAULT_TEMP = 20.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TadoResumeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a climate entity for each room that supports a target temperature."""
    data = entry.runtime_data
    caps = data.coordinator.capabilities
    async_add_entities(
        TadoClimate(entry, room["id"], room["name"])
        for room in data.rooms
        if CAP_TARGET in caps.get(room["id"], frozenset())
    )
    entity_platform.async_get_current_platform().async_register_entity_service(
        SERVICE_SET_ROOM_TEMPERATURE,
        {
            vol.Required(ATTR_TEMPERATURE): vol.Coerce(float),
            vol.Optional("termination", default=TERMINATION_NEXT_BLOCK): vol.In(
                TERMINATIONS
            ),
            vol.Optional("duration"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        },
        "async_set_room_temperature",
    )


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


class TadoClimate(CoordinatorEntity, ClimateEntity):
    """A tado room (or zone) as a heating thermostat."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = 0.5
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]

    def __init__(
        self, entry: TadoResumeConfigEntry, room_id: int, room_name: str
    ) -> None:
        data = entry.runtime_data
        super().__init__(data.coordinator)
        self._data = data
        self._room_id = room_id
        self._attr_unique_id = f"{data.home_id}_{room_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{data.home_id}_{room_id}")},
            name=room_name,
            manufacturer="tado°",
        )
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        if data.generation == GENERATION_X:
            features |= ClimateEntityFeature.PRESET_MODE
            self._attr_preset_modes = [PRESET_SCHEDULE, PRESET_BOOST]
        self._attr_supported_features = features

    @property
    def _room(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("rooms", {}).get(self._room_id, {})

    @property
    def _setting(self) -> dict[str, Any]:
        return self._room.get("setting") or {}

    @property
    def _overridden(self) -> bool:
        room = self._room
        return bool(room.get("manualControlTermination") or room.get("overlay"))

    @property
    def available(self) -> bool:
        return super().available and bool(self._room)

    @property
    def current_temperature(self) -> float | None:
        inside = (self._room.get("sensorDataPoints") or {}).get("insideTemperature")
        inside = inside or {}
        return _number(inside.get("value", inside.get("celsius")))

    @property
    def current_humidity(self) -> float | None:
        humidity = (self._room.get("sensorDataPoints") or {}).get("humidity") or {}
        return _number(humidity.get("percentage"))

    @property
    def target_temperature(self) -> float | None:
        if self._setting.get("power") == "OFF":
            return None
        temp = self._setting.get("temperature") or {}
        return _number(temp.get("value", temp.get("celsius")))

    @property
    def hvac_mode(self) -> HVACMode:
        if self._setting.get("power") == "OFF":
            return HVACMode.OFF
        return HVACMode.HEAT if self._overridden else HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction:
        if self._setting.get("power") == "OFF":
            return HVACAction.OFF
        power = self._room.get("heatingPower")
        if power is None:
            power = (self._room.get("activityDataPoints") or {}).get("heatingPower")
        percentage = _number((power or {}).get("percentage")) or 0
        return HVACAction.HEATING if percentage > 0 else HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        if self._data.generation != GENERATION_X:
            return None
        if self._room.get("boostMode") or self._setting.get("isBoost"):
            return PRESET_BOOST
        return None if self._overridden else PRESET_SCHEDULE

    async def _call(self, coro) -> None:
        try:
            await coro
        except TadoError as err:
            raise HomeAssistantError(f"tado request failed: {err}") from err
        await self.coordinator.async_request_refresh()

    async def _resume(self) -> None:
        await self._call(
            self._data.api.async_resume_room(
                self._data.home_id, self._data.generation, self._room_id
            )
        )

    async def _manual(
        self,
        temperature: float | None,
        termination: str = TERMINATION_NEXT_BLOCK,
        duration: int | None = None,
        boost: bool = False,
    ) -> None:
        await self._call(
            self._data.api.async_set_manual(
                self._data.home_id,
                self._data.generation,
                self._room_id,
                temperature,
                termination,
                duration,
                boost,
            )
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a target temperature until the next schedule block."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self._manual(float(temperature))

    async def async_set_room_temperature(
        self,
        temperature: float,
        termination: str = TERMINATION_NEXT_BLOCK,
        duration: int | None = None,
    ) -> None:
        """Entity service: set a target with a chosen termination (minutes)."""
        seconds = duration * 60 if duration else None
        if termination == TERMINATION_TIMER and not seconds:
            raise HomeAssistantError("A duration is required for a timed override")
        await self._manual(float(temperature), termination, seconds)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Resume the schedule, hold a manual target, or turn heating off."""
        if hvac_mode == HVACMode.AUTO:
            await self._resume()
        elif hvac_mode == HVACMode.OFF:
            await self._manual(None, TERMINATION_NEXT_BLOCK)
        else:
            await self._manual(self.target_temperature or DEFAULT_TEMP)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Boost the room for 30 minutes, or resume the schedule."""
        if preset_mode == PRESET_BOOST:
            await self._call(
                self._data.api.async_boost_room(
                    self._data.home_id, self._data.generation, self._room_id
                )
            )
        else:
            await self._resume()
