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

from .api import TadoApi, TadoAuthError, TadoError, TadoRateLimitError
from .capabilities import capability_map
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN
from .devices import parse_devices, tracked_mobiles

_LOGGER = logging.getLogger(__name__)

MAX_INTERVAL = timedelta(minutes=15)
AWAY_FACTOR = 3  # poll this many times slower while the home is away
FAILURE_REPAIR_AFTER = timedelta(hours=1)
ISSUE_API_UNREACHABLE = "api_unreachable"


class TadoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch home state; back off exponentially while the API is failing."""

    def __init__(
        self, hass: HomeAssistant, entry: Any, api: TadoApi, home_id: int, generation: str
    ) -> None:
        interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{home_id}",
            update_interval=timedelta(seconds=interval),
        )
        self.base_interval = timedelta(seconds=interval)
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
            backoff = min(
                (self.update_interval or self.base_interval) * 2,
                max(MAX_INTERVAL, self.base_interval),
            )
            if isinstance(err, TadoRateLimitError) and err.retry_after:
                backoff = max(backoff, timedelta(seconds=err.retry_after))
            self.update_interval = backoff
            self._note_failure()
            raise UpdateFailed(str(err)) from err
        self.update_interval = self._steady_interval(state)
        self.last_success = dt_util.utcnow()
        self._failing_since = None
        self.clear_issue()
        self.capabilities = capability_map(state)
        self.devices = {d["serial"]: d for d in parse_devices(state.get("devices"))}
        self.mobiles = tracked_mobiles(state.get("mobile_devices"))
        return state

    def _steady_interval(self, state: dict[str, Any]) -> timedelta:
        """Poll slower while the home is away; nothing changes quickly then."""
        presence = state.get("presence")
        if isinstance(presence, dict) and str(presence.get("presence", "")).upper() == "AWAY":
            return self.base_interval * AWAY_FACTOR
        return self.base_interval

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
