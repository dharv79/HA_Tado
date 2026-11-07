"""Home Assistant for Tado Thermostat integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TadoApi, TadoAuthError, TadoError
from .coordinator import TadoCoordinator
from .const import (
    CONF_GENERATION,
    CONF_HOME_ID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    SERVICE_BOOST_ALL,
    SERVICE_RESUME_ALL,
    SERVICE_TURN_OFF_ALL,
)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.DEVICE_TRACKER,
    Platform.SELECT,
    Platform.SENSOR,
]


@dataclass
class TadoResumeData:
    """Runtime data for a config entry."""

    api: TadoApi
    home_id: int
    generation: str
    rooms: list[dict]
    coordinator: TadoCoordinator


type TadoResumeConfigEntry = ConfigEntry[TadoResumeData]


def _home_service(hass: HomeAssistant, method: str):
    """Build a service that runs a whole-home API action for every home."""

    async def _handler(call: ServiceCall) -> None:
        for loaded in hass.config_entries.async_loaded_entries(DOMAIN):
            data = loaded.runtime_data
            try:
                await getattr(data.api, method)(
                    data.home_id, data.generation, [r["id"] for r in data.rooms]
                )
            except TadoError as err:
                raise HomeAssistantError(f"Request failed: {err}") from err
            await data.coordinator.async_request_refresh()

    return _handler


async def async_setup_entry(hass: HomeAssistant, entry: TadoResumeConfigEntry) -> bool:
    """Set up a tado home."""

    async def _store_token(token: str) -> None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_REFRESH_TOKEN: token}
        )

    api = TadoApi(
        async_get_clientsession(hass), entry.data[CONF_REFRESH_TOKEN], _store_token
    )
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

    if not hass.services.has_service(DOMAIN, SERVICE_RESUME_ALL):
        for service, method in (
            (SERVICE_RESUME_ALL, "async_resume_all"),
            (SERVICE_BOOST_ALL, "async_boost_all"),
            (SERVICE_TURN_OFF_ALL, "async_turn_off_all"),
        ):
            hass.services.async_register(DOMAIN, service, _home_service(hass, method))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TadoResumeConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        for service in (SERVICE_RESUME_ALL, SERVICE_BOOST_ALL, SERVICE_TURN_OFF_ALL):
            hass.services.async_remove(DOMAIN, service)
    return unloaded
