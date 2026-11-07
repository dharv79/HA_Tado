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
    SERVICE_RESUME_ALL,
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

        async def _resume_all(call: ServiceCall) -> None:
            for loaded in hass.config_entries.async_loaded_entries(DOMAIN):
                data = loaded.runtime_data
                try:
                    await data.api.async_resume_all(
                        data.home_id, data.generation, [r["id"] for r in data.rooms]
                    )
                except TadoError as err:
                    raise HomeAssistantError(f"Resume failed: {err}") from err
                await data.coordinator.async_request_refresh()

        hass.services.async_register(DOMAIN, SERVICE_RESUME_ALL, _resume_all)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TadoResumeConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_RESUME_ALL)
    return unloaded
