"""Polling coordinator for a tado home."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TadoApi, TadoAuthError, TadoError
from .capabilities import capability_map
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BASE_INTERVAL = timedelta(seconds=60)
MAX_INTERVAL = timedelta(minutes=15)


class TadoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch home state; back off exponentially while the API is failing."""

    def __init__(
        self, hass: HomeAssistant, entry: Any, api: TadoApi, home_id: int, generation: str
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{home_id}",
            update_interval=BASE_INTERVAL,
        )
        self.api = api
        self.home_id = home_id
        self.generation = generation
        self.capabilities: dict[int, frozenset[str]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            state = await self.api.async_get_state(self.home_id, self.generation)
        except TadoAuthError as err:
            raise ConfigEntryAuthFailed from err
        except TadoError as err:
            self.update_interval = min(self.update_interval * 2, MAX_INTERVAL)
            raise UpdateFailed(str(err)) from err
        self.update_interval = BASE_INTERVAL
        self.capabilities = capability_map(state)
        return state
