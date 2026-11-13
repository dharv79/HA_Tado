"""Minimal tado API client supporting tado X and classic (v2) homes."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .const import DEFAULT_BOOST_MINUTES, DEFAULT_BOOST_TEMPERATURE

_LOGGER = logging.getLogger(__name__)

CLIENT_ID = "1bb50063-6b0c-4d11-bd99-387f4a91cc46"
LOGIN_URL = "https://login.tado.com/oauth2"
DEVICE_AUTHORIZE_URL = f"{LOGIN_URL}/device_authorize"
TOKEN_URL = f"{LOGIN_URL}/token"
CLASSIC_API = "https://my.tado.com/api/v2"
X_API = "https://hops.tado.com"

GENERATION_X = "LINE_X"
GENERATION_CLASSIC = "PRE_LINE_X"

TERMINATION_NEXT_BLOCK = "next_schedule_block"
TERMINATION_TIMER = "duration"
TERMINATION_MANUAL = "indefinite"
TERMINATIONS = (TERMINATION_NEXT_BLOCK, TERMINATION_TIMER, TERMINATION_MANUAL)

PRESENCE_HOME = "home"
PRESENCE_AWAY = "away"
PRESENCE_AUTO = "auto"
PRESENCE_OPTIONS = (PRESENCE_HOME, PRESENCE_AWAY, PRESENCE_AUTO)


_X_TERMINATION = {
    TERMINATION_NEXT_BLOCK: "NEXT_TIME_BLOCK",
    TERMINATION_TIMER: "TIMER",
    TERMINATION_MANUAL: "MANUAL",
}
_CLASSIC_TERMINATION = {
    TERMINATION_NEXT_BLOCK: "TADO_MODE",
    TERMINATION_TIMER: "TIMER",
    TERMINATION_MANUAL: "MANUAL",
}

_TOKEN_MARGIN = 30
OPTIONAL_BACKOFF = 1800  # seconds to leave a failing optional endpoint alone
MAX_RETRY_AFTER = 3600


class TadoError(Exception):
    """Generic tado API error."""


class TadoAuthError(TadoError):
    """Authentication failed; the user must log in again."""


class TadoRateLimitError(TadoError):
    """tado answered 429; retry_after is the requested wait in seconds, if given."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TadoAuthPending(TadoError):
    """The user has not yet approved the device login."""


async def async_start_device_flow(session: aiohttp.ClientSession) -> dict[str, Any]:
    """Start the OAuth device-code flow."""
    async with session.post(
        DEVICE_AUTHORIZE_URL,
        data={"client_id": CLIENT_ID, "scope": "offline_access"},
    ) as resp:
        if resp.status != 200:
            raise TadoError(f"Device authorisation failed ({resp.status})")
        return await resp.json()


async def async_poll_device_flow(
    session: aiohttp.ClientSession, device_code: str
) -> dict[str, Any]:
    """Exchange a device code for tokens once the user has approved."""
    return await _token_request(
        session,
        {
            "client_id": CLIENT_ID,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        },
    )


async def _token_request(session: aiohttp.ClientSession, data: dict[str, str]) -> dict[str, Any]:
    async with session.post(TOKEN_URL, data=data) as resp:
        try:
            body = await resp.json()
        except (aiohttp.ContentTypeError, ValueError):
            body = {}
        if resp.status == 200:
            return body
        error = body.get("error")
        if error in ("authorization_pending", "slow_down"):
            raise TadoAuthPending(error)
        if resp.status in (400, 401, 403):
            raise TadoAuthError(error or f"Authentication failed ({resp.status})")
        raise TadoError(f"Token request failed ({resp.status})")


def _retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header given in seconds."""
    try:
        seconds = float(value) if value is not None else None
    except ValueError:
        return None
    if seconds is None or seconds < 0:
        return None
    return min(seconds, MAX_RETRY_AFTER)


class TadoApi:
    """Authenticated tado client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        refresh_token: str,
        token_updated: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._session = session
        self._refresh_token = refresh_token
        self._token_updated = token_updated
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._refresh_lock = asyncio.Lock()
        self._optional_until: dict[str, float] = {}
        self._optional_last: dict[str, Any] = {}

    async def _async_ensure_token(self, stale: str | None = None) -> str:
        """Return a valid access token, refreshing at most once concurrently.

        Refresh tokens are single use, so parallel refreshes would invalidate
        each other. `stale` is a token the server rejected.
        """
        async with self._refresh_lock:
            return await self._async_refresh(stale)

    async def _async_refresh(self, stale: str | None) -> str:
        if (
            self._access_token
            and self._access_token != stale
            and time.monotonic() < self._expires_at
        ):
            return self._access_token
        tokens = await _token_request(
            self._session,
            {
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
        )
        self._access_token = tokens["access_token"]
        self._expires_at = time.monotonic() + int(tokens.get("expires_in", 600)) - _TOKEN_MARGIN
        new_refresh = tokens.get("refresh_token")
        if new_refresh and new_refresh != self._refresh_token:
            self._refresh_token = new_refresh
            if self._token_updated:
                await self._token_updated(new_refresh)
        return self._access_token

    async def _request(self, method: str, url: str, json: dict[str, Any] | None = None) -> Any:
        token: str | None = None
        for attempt in (0, 1):
            token = await self._async_ensure_token(stale=token if attempt else None)
            headers = {"Authorization": f"Bearer {token}"}
            if method in ("POST", "PUT", "PATCH"):
                # tado X rejects body-less writes without a JSON content type.
                headers["Content-Type"] = "application/json"
            async with self._session.request(method, url, headers=headers, json=json) as resp:
                if resp.status == 401 and attempt == 0:
                    continue
                if resp.status == 401:
                    raise TadoAuthError("Unauthorised")
                if method != "GET":
                    _LOGGER.info(
                        "tado write %s %s -> %s %s",
                        method,
                        url,
                        resp.status,
                        (await resp.text())[:200],
                    )
                if resp.status == 429:
                    raise TadoRateLimitError(
                        f"{method} {url} rate limited (429)",
                        _retry_after(resp.headers.get("Retry-After")),
                    )
                if resp.status >= 400:
                    detail = (await resp.text())[:300]
                    raise TadoError(f"{method} {url} failed ({resp.status}): {detail}")
                if resp.status == 204 or resp.content_length == 0:
                    return None
                try:
                    return await resp.json()
                except (aiohttp.ContentTypeError, ValueError):
                    return None

    async def async_get_homes(self) -> list[dict[str, Any]]:
        """Return the homes on the account."""
        me = await self._request("GET", f"{CLASSIC_API}/me")
        return me.get("homes", [])

    async def async_get_generation(self, home_id: int) -> str:
        """Return the home generation (LINE_X or PRE_LINE_X)."""
        home = await self._request("GET", f"{CLASSIC_API}/homes/{home_id}")
        return home.get("generation", GENERATION_CLASSIC)

    async def async_get_rooms(self, home_id: int, generation: str) -> list[dict[str, Any]]:
        """Return rooms (tado X) or zones (classic) as [{id, name}]."""
        if generation == GENERATION_X:
            data = await self._request("GET", f"{X_API}/homes/{home_id}/rooms")
        else:
            data = await self._request("GET", f"{CLASSIC_API}/homes/{home_id}/zones")
        return [{"id": item["id"], "name": item["name"]} for item in data or []]

    async def async_resume_room(self, home_id: int, generation: str, room_id: int) -> None:
        """Remove any manual override and resume the room's schedule."""
        if generation == GENERATION_X:
            await self._request("POST", f"{X_API}/homes/{home_id}/rooms/{room_id}/resumeSchedule")
        else:
            await self._request("DELETE", f"{CLASSIC_API}/homes/{home_id}/zones/{room_id}/overlay")

    async def async_resume_all(self, home_id: int, generation: str, room_ids: list[int]) -> None:
        """Resume the schedule in every room of the home."""
        if generation == GENERATION_X:
            await self._request("POST", f"{X_API}/homes/{home_id}/quickActions/resumeSchedule")
            return
        for room_id in room_ids:
            await self.async_resume_room(home_id, generation, room_id)

    async def async_boost_all(self, home_id: int, generation: str, room_ids: list[int]) -> None:
        """Boost every room (tado X only)."""
        if generation != GENERATION_X:
            raise TadoError("Boost is only supported on tado X")
        await self._request("POST", f"{X_API}/homes/{home_id}/quickActions/boost")

    async def async_turn_off_all(self, home_id: int, generation: str, room_ids: list[int]) -> None:
        """Switch heating off in every room until the next schedule block."""
        if generation == GENERATION_X:
            await self._request("POST", f"{X_API}/homes/{home_id}/quickActions/turnOffAll")
            return
        for room_id in room_ids:
            await self.async_set_manual(home_id, generation, room_id, None)

    async def async_set_presence(self, home_id: int, generation: str, presence: str) -> None:
        """Set home presence: "home", "away" or "auto" (geofencing)."""
        if presence not in PRESENCE_OPTIONS:
            raise TadoError(f"Unknown presence: {presence}")
        if generation == GENERATION_X:
            await self._request(
                "PUT",
                f"{X_API}/homes/{home_id}/presence",
                {"homePresence": presence.upper()},
            )
        elif presence == PRESENCE_AUTO:
            await self._request("DELETE", f"{CLASSIC_API}/homes/{home_id}/presenceLock")
        else:
            await self._request(
                "PUT",
                f"{CLASSIC_API}/homes/{home_id}/presenceLock",
                {"homePresence": presence.upper()},
            )

    async def async_set_temperature_offset(
        self, home_id: int, generation: str, serial: str, offset: float
    ) -> None:
        """Set a device's temperature offset in °C (tado X only)."""
        if generation != GENERATION_X:
            raise TadoError("Temperature offset is only supported on tado X")
        await self._request(
            "PATCH",
            f"{X_API}/homes/{home_id}/roomsAndDevices/devices/{serial}",
            {"temperatureOffset": offset},
        )

    async def async_set_child_lock(
        self, home_id: int, generation: str, serial: str, enabled: bool
    ) -> None:
        """Enable or disable a device's child lock."""
        body = {"childLockEnabled": enabled}
        if generation == GENERATION_X:
            await self._request(
                "PATCH", f"{X_API}/homes/{home_id}/roomsAndDevices/devices/{serial}", body
            )
        else:
            await self._request("PUT", f"{CLASSIC_API}/devices/{serial}/childLock", body)

    async def _optional(self, url: str) -> Any:
        """GET an endpoint that may be unavailable for some homes.

        After a failure the endpoint is skipped for OPTIONAL_BACKOFF seconds and
        the last good payload (if any) is returned instead.
        """
        if time.monotonic() < self._optional_until.get(url, 0.0):
            return self._optional_last.get(url)
        try:
            data = await self._request("GET", url)
        except (TadoAuthError, TadoRateLimitError):
            raise
        except TadoError:
            self._optional_until[url] = time.monotonic() + OPTIONAL_BACKOFF
            return self._optional_last.get(url)
        self._optional_until.pop(url, None)
        self._optional_last[url] = data
        return data

    async def async_get_state(self, home_id: int, generation: str) -> dict[str, Any]:
        """Return a snapshot of the home: rooms, devices, presence, weather.

        Rooms are required; the other sections are optional and are None when
        the endpoint is unavailable. Payloads are kept as returned by tado.
        """
        classic = f"{CLASSIC_API}/homes/{home_id}"
        x_home = f"{X_API}/homes/{home_id}"
        if generation == GENERATION_X:
            rooms, devices, presence, weather, mobiles = await asyncio.gather(
                self._request("GET", f"{x_home}/rooms"),
                self._optional(f"{x_home}/roomsAndDevices"),
                self._optional(f"{x_home}/state"),
                self._optional(f"{classic}/weather"),
                self._optional(f"{classic}/mobileDevices"),
            )
        else:
            zones, devices, presence, weather, mobiles = await asyncio.gather(
                self._request("GET", f"{classic}/zones"),
                self._optional(f"{classic}/devices"),
                self._optional(f"{classic}/state"),
                self._optional(f"{classic}/weather"),
                self._optional(f"{classic}/mobileDevices"),
            )
            states = await asyncio.gather(
                *(self._optional(f"{classic}/zones/{zone['id']}/state") for zone in zones or [])
            )
            rooms = [
                {**zone, **(state or {})} for zone, state in zip(zones or [], states, strict=False)
            ]
        return {
            "rooms": {room["id"]: room for room in rooms or []},
            "devices": devices,
            "presence": presence,
            "weather": weather,
            "mobile_devices": mobiles,
        }

    async def async_set_manual(
        self,
        home_id: int,
        generation: str,
        room_id: int,
        temperature: float | None,
        termination: str = TERMINATION_NEXT_BLOCK,
        duration: int | None = None,
        boost: bool = False,
    ) -> None:
        """Override a room's schedule.

        A temperature of None switches heating off (frost protection).
        ``duration`` (seconds) is required for the timer termination.
        Boost is supported on tado X only.
        """
        if termination not in TERMINATIONS:
            raise TadoError(f"Unknown termination type: {termination}")
        if termination == TERMINATION_TIMER and not duration:
            raise TadoError("A duration is required for a timed override")
        if boost and generation != GENERATION_X:
            raise TadoError("Boost is only supported on tado X")
        if generation == GENERATION_X:
            setting: dict[str, Any] = {"power": "OFF"}
            if temperature is not None:
                setting = {
                    "power": "ON",
                    "isBoost": str(boost),
                    "temperature": {"value": f"{temperature}"},
                }
            term: dict[str, Any] = {"type": _X_TERMINATION[termination]}
            if termination == TERMINATION_TIMER:
                term["durationInSeconds"] = f"{duration}"
            await self._request(
                "POST",
                f"{X_API}/homes/{home_id}/rooms/{room_id}/manualControl",
                {"setting": setting, "termination": term},
            )
            return
        setting = {"type": "HEATING", "power": "OFF"}
        if temperature is not None:
            setting = {
                "type": "HEATING",
                "power": "ON",
                "temperature": {"celsius": temperature},
            }
        term = {"typeSkillBasedApp": _CLASSIC_TERMINATION[termination]}
        if termination == TERMINATION_TIMER:
            term["durationInSeconds"] = duration
        await self._request(
            "PUT",
            f"{CLASSIC_API}/homes/{home_id}/zones/{room_id}/overlay",
            {"setting": setting, "termination": term},
        )

    async def async_boost_room(
        self,
        home_id: int,
        generation: str,
        room_id: int,
        temperature: float = DEFAULT_BOOST_TEMPERATURE,
        seconds: int = DEFAULT_BOOST_MINUTES * 60,
    ) -> None:
        """Boost a room (tado X only); 25 °C for 30 minutes unless told otherwise."""
        await self.async_set_manual(
            home_id,
            generation,
            room_id,
            temperature,
            TERMINATION_TIMER,
            seconds,
            boost=True,
        )
