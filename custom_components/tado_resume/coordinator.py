"""Polling coordinator for a tado home."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import TadoApi, TadoAuthError, TadoError
from .capabilities import capability_map
from .const import DOMAIN
from .devices import parse_devices, tracked_mobiles

_LOGGER = logging.getLogger(__name__)

BASE_INTERVAL = timedelta(seconds=60)
MAX_INTERVAL = timedelta(minutes=15)
FAILURE_REPAIR_AFTER = timedelta(hours=1)
ISSUE_API_UNREACHABLE = "api_unreachable"


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
        self.devices: dict[str, dict[str, Any]] = {}
        self.mobiles: dict[Any, dict[str, Any]] = {}
        self.last_success: datetime | None = None
        self._failing_since: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            state = await self.api.async_get_state(self.home_id, self.generation)
        except TadoAuthError as err:
            raise ConfigEntryAuthFailed from err
        except TadoError as err:
            self.update_interval = min((self.update_interval or BASE_INTERVAL) * 2, MAX_INTERVAL)
            self._note_failure()
            raise UpdateFailed(str(err)) from err
        self.update_interval = BASE_INTERVAL
        self.last_success = dt_util.utcnow()
        self._failing_since = None
        self.clear_issue()
        self.capabilities = capability_map(state)
        self.devices = {d["serial"]: d for d in parse_devices(state.get("devices"))}
        self.mobiles = tracked_mobiles(state.get("mobile_devices"))
        return state

    def _note_failure(self) -> None:
        """Raise a repair issue once the API has failed for a sustained period."""
        now = dt_util.utcnow()
        if self._failing_since is None:
            self._failing_since = now
        if now - self._failing_since >= FAILURE_REPAIR_AFTER:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"{ISSUE_API_UNREACHABLE}_{self.home_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_API_UNREACHABLE,
            )

    def clear_issue(self) -> None:
        """Remove the repair issue, if present."""
        ir.async_delete_issue(self.hass, DOMAIN, f"{ISSUE_API_UNREACHABLE}_{self.home_id}")
