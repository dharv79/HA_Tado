"""Home Assistant for Tado Thermostat integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .api import TadoApi, TadoAuthError, TadoError
from .away import AwayTimer
from .const import (
    CONF_GENERATION,
    CONF_HOME_ID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    SERVICE_BOOST_ALL,
    SERVICE_RESUME_ALL,
    SERVICE_SET_AWAY_UNTIL,
    SERVICE_TURN_OFF_ALL,
)
from .coordinator import TadoCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.DEVICE_TRACKER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

HOME_SERVICES = {
    SERVICE_RESUME_ALL: "async_resume_all",
    SERVICE_BOOST_ALL: "async_boost_all",
    SERVICE_TURN_OFF_ALL: "async_turn_off_all",
}


@dataclass
class TadoResumeData:
    """Runtime data for a config entry."""

    api: TadoApi
    home_id: int
    generation: str
    rooms: list[dict]
    coordinator: TadoCoordinator
    away: AwayTimer | None = None

    @property
    def room_ids(self) -> list[int]:
        """IDs of all rooms in the home."""
        return [room["id"] for room in self.rooms]


type TadoResumeConfigEntry = ConfigEntry[TadoResumeData]


def _home_service(hass: HomeAssistant, method: str):
    """Build a service that runs a whole-home API action for every home."""

    async def _handler(call: ServiceCall) -> None:
        for loaded in hass.config_entries.async_loaded_entries(DOMAIN):
            data = loaded.runtime_data
            try:
                await getattr(data.api, method)(data.home_id, data.generation, data.room_ids)
            except TadoError as err:
                raise HomeAssistantError(f"Request failed: {err}") from err
            await data.coordinator.async_request_refresh()

    return _handler


def _away_until_service(hass: HomeAssistant):
    """Build the set_away_until service handler."""

    async def _handler(call: ServiceCall) -> None:
        await _async_set_away_until(hass, call)

    return _handler


async def _async_set_away_until(hass: HomeAssistant, call: ServiceCall) -> None:
    """Set every home away now and return it to automatic at the given time."""
    until: datetime = dt_util.as_utc(call.data["until"])
    if until <= dt_util.utcnow():
        raise ServiceValidationError("The away end time must be in the future")
    for loaded in hass.config_entries.async_loaded_entries(DOMAIN):
        timer = loaded.runtime_data.away
        if timer is None:
            continue
        try:
            await timer.async_start(until)
        except TadoError as err:
            raise HomeAssistantError(f"Request failed: {err}") from err
        await loaded.runtime_data.coordinator.async_request_refresh()


def _remove_open_window_buttons(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the open-window buttons created by 0.5.0 to 0.6.1."""
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id.endswith(("_open_window_activate", "_open_window_reset")):
            registry.async_remove(entity.entity_id)


async def _async_options_updated(hass: HomeAssistant, entry: TadoResumeConfigEntry) -> None:
    """Reload so changed options take effect without a restart."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: TadoResumeConfigEntry) -> bool:
    """Set up a tado home."""

    async def _store_token(token: str) -> None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_REFRESH_TOKEN: token}
        )

    api = TadoApi(async_get_clientsession(hass), entry.data[CONF_REFRESH_TOKEN], _store_token)
    home_id = entry.data[CONF_HOME_ID]
    generation = entry.data[CONF_GENERATION]
    try:
        rooms = await api.async_get_rooms(home_id, generation)
    except TadoAuthError as err:
        raise ConfigEntryAuthFailed from err
    except TadoError as err:
        raise ConfigEntryNotReady from err

    coordinator = TadoCoordinator(hass, entry, api, home_id, generation)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = TadoResumeData(api, home_id, generation, rooms, coordinator)
    entry.runtime_data.away = AwayTimer(hass, entry.entry_id, entry.runtime_data)
    await entry.runtime_data.away.async_restore()

    if not hass.services.has_service(DOMAIN, SERVICE_RESUME_ALL):
        for service, method in HOME_SERVICES.items():
            hass.services.async_register(DOMAIN, service, _home_service(hass, method))
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_AWAY_UNTIL,
            _away_until_service(hass),
            schema=vol.Schema({vol.Required("until"): cv.datetime}),
        )

    _remove_open_window_buttons(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TadoResumeConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.coordinator.clear_issue()
        if entry.runtime_data.away:
            entry.runtime_data.away.async_shutdown()
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        for service in (*HOME_SERVICES, SERVICE_SET_AWAY_UNTIL):
            hass.services.async_remove(DOMAIN, service)
    return unloaded
