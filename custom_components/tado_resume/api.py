"""Minimal tado API client supporting tado X and classic (v2) homes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import time
from typing import Any

import aiohttp

CLIENT_ID = "1bb50063-6b0c-4d11-bd99-387f4a91cc46"
LOGIN_URL = "https://login.tado.com/oauth2"
DEVICE_AUTHORIZE_URL = f"{LOGIN_URL}/device_authorize"
TOKEN_URL = f"{LOGIN_URL}/token"
CLASSIC_API = "https://my.tado.com/api/v2"
X_API = "https://hops.tado.com"

GENERATION_X = "LINE_X"
GENERATION_CLASSIC = "PRE_LINE_X"

_TOKEN_MARGIN = 30


class TadoError(Exception):
    """Generic tado API error."""


class TadoAuthError(TadoError):
    """Authentication failed; the user must log in again."""


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


async def _token_request(
    session: aiohttp.ClientSession, data: dict[str, str]
) -> dict[str, Any]:
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

    async def _async_ensure_token(self, force: bool = False) -> str:
        if not force and self._access_token and time.monotonic() < self._expires_at:
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
        self._expires_at = (
            time.monotonic() + int(tokens.get("expires_in", 600)) - _TOKEN_MARGIN
        )
        new_refresh = tokens.get("refresh_token")
        if new_refresh and new_refresh != self._refresh_token:
            self._refresh_token = new_refresh
            if self._token_updated:
                await self._token_updated(new_refresh)
        return self._access_token

    async def _request(self, method: str, url: str) -> Any:
        for attempt in (0, 1):
            token = await self._async_ensure_token(force=attempt == 1)
            headers = {"Authorization": f"Bearer {token}"}
            if method in ("POST", "PUT", "PATCH"):
                # tado X rejects body-less writes without a JSON content type.
                headers["Content-Type"] = "application/json"
            async with self._session.request(method, url, headers=headers) as resp:
                if resp.status == 401 and attempt == 0:
                    continue
                if resp.status == 401:
                    raise TadoAuthError("Unauthorised")
                if resp.status >= 400:
                    detail = (await resp.text())[:300]
                    raise TadoError(
                        f"{method} {url} failed ({resp.status}): {detail}"
                    )
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

    async def async_get_rooms(
        self, home_id: int, generation: str
    ) -> list[dict[str, Any]]:
        """Return rooms (tado X) or zones (classic) as [{id, name}]."""
        if generation == GENERATION_X:
            data = await self._request("GET", f"{X_API}/homes/{home_id}/rooms")
        else:
            data = await self._request("GET", f"{CLASSIC_API}/homes/{home_id}/zones")
        return [{"id": item["id"], "name": item["name"]} for item in data or []]

    async def async_resume_room(
        self, home_id: int, generation: str, room_id: int
    ) -> None:
        """Remove any manual override and resume the room's schedule."""
        if generation == GENERATION_X:
            await self._request(
                "POST", f"{X_API}/homes/{home_id}/rooms/{room_id}/resumeSchedule"
            )
        else:
            await self._request(
                "DELETE", f"{CLASSIC_API}/homes/{home_id}/zones/{room_id}/overlay"
            )

    async def async_resume_all(
        self, home_id: int, generation: str, room_ids: list[int]
    ) -> None:
        """Resume the schedule in every room of the home."""
        if generation == GENERATION_X:
            await self._request(
                "POST", f"{X_API}/homes/{home_id}/quickActions/resumeSchedule"
            )
            return
        for room_id in room_ids:
            await self.async_resume_room(home_id, generation, room_id)

    async def _optional(self, url: str) -> Any:
        """GET an endpoint that may be unavailable for some homes."""
        try:
            return await self._request("GET", url)
        except TadoAuthError:
            raise
        except TadoError:
            return None

    async def async_get_state(
        self, home_id: int, generation: str
    ) -> dict[str, Any]:
        """Return a snapshot of the home: rooms, devices, presence, weather.

        Rooms are required; the other sections are optional and are None when
        the endpoint is unavailable. Payloads are kept as returned by tado.
        """
        classic = f"{CLASSIC_API}/homes/{home_id}"
        if generation == GENERATION_X:
            rooms = await self._request("GET", f"{X_API}/homes/{home_id}/rooms")
            devices = await self._optional(f"{X_API}/homes/{home_id}/roomsAndDevices")
            presence = await self._optional(f"{X_API}/homes/{home_id}/state")
        else:
            zones = await self._request("GET", f"{classic}/zones")
            rooms = []
            for zone in zones or []:
                state = await self._optional(f"{classic}/zones/{zone['id']}/state")
                rooms.append({**zone, **(state or {})})
            devices = await self._optional(f"{classic}/devices")
            presence = await self._optional(f"{classic}/state")
        return {
            "rooms": {room["id"]: room for room in rooms or []},
            "devices": devices,
            "presence": presence,
            "weather": await self._optional(f"{classic}/weather"),
            "mobile_devices": await self._optional(f"{classic}/mobileDevices"),
        }
