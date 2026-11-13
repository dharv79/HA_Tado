"""Timed away: set presence to away and return to automatic at a chosen time."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import PRESENCE_AUTO, PRESENCE_AWAY, TadoError
from .const import DOMAIN

if TYPE_CHECKING:
    from . import TadoResumeData

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
RETRY_DELAY = timedelta(minutes=5)


class AwayTimer:
    """Holds the end time of a timed away period and survives restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str, data: TadoResumeData) -> None:
        self._hass = hass
        self._data = data
        self._store: Store[dict[str, str]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.away_{entry_id}"
        )
        self._until: datetime | None = None
        self._unsub: CALLBACK_TYPE | None = None

    @property
    def until(self) -> datetime | None:
        """End of the current timed away period, if any."""
        return self._until

    async def async_restore(self) -> None:
        """Resume a stored timer; an elapsed one returns presence to automatic."""
        stored = await self._store.async_load()
        until = dt_util.parse_datetime(stored["until"]) if stored and "until" in stored else None
        if until is None:
            return
        self._until = until
        if until <= dt_util.utcnow():
            await self._async_finish()
        else:
            self._schedule(until)

    async def async_start(self, until: datetime) -> None:
        """Set presence to away now and return to automatic at ``until``."""
        data = self._data
        await data.api.async_set_presence(data.home_id, data.generation, PRESENCE_AWAY)
        self._until = until
        await self._store.async_save({"until": until.isoformat()})
        self._schedule(until)

    async def async_cancel(self) -> None:
        """Forget the timer without changing presence."""
        self._unschedule()
        self._until = None
        await self._store.async_remove()

    @callback
    def async_shutdown(self) -> None:
        """Stop the in-memory timer; the stored end time is kept for the next start."""
        self._unschedule()

    def _unschedule(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    def _schedule(self, when: datetime) -> None:
        self._unschedule()
        self._unsub = async_track_point_in_utc_time(self._hass, self._async_fire, when)

    async def _async_fire(self, _now: datetime) -> None:
        self._unsub = None
        await self._async_finish()

    async def _async_finish(self) -> None:
        data = self._data
        try:
            await data.api.async_set_presence(data.home_id, data.generation, PRESENCE_AUTO)
        except TadoError as err:
            _LOGGER.warning("Could not end timed away, retrying in 5 minutes: %s", err)
            self._schedule(dt_util.utcnow() + RETRY_DELAY)
            return
        await self.async_cancel()
        await data.coordinator.async_request_refresh()
