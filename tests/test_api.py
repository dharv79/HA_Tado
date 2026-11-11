"""API client tests with a mocked tado."""

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.tado_resume.api import (
    CLASSIC_API,
    GENERATION_CLASSIC,
    GENERATION_X,
    TOKEN_URL,
    X_API,
    TadoApi,
    TadoAuthError,
    TadoAuthPending,
    TadoError,
    async_poll_device_flow,
)

TOKEN = {"access_token": "a", "refresh_token": "r2", "expires_in": 600}


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


async def test_resume_room_x(session):
    with aioresponses() as m:
        m.post(TOKEN_URL, payload=TOKEN)
        m.post(f"{X_API}/homes/1/rooms/5/resumeSchedule", status=204)
        await TadoApi(session, "r").async_resume_room(1, GENERATION_X, 5)
        assert any("resumeSchedule" in str(k[1]) for k in m.requests)


async def test_resume_room_classic_deletes_overlay(session):
    with aioresponses() as m:
        m.post(TOKEN_URL, payload=TOKEN)
        m.delete(f"{CLASSIC_API}/homes/1/zones/2/overlay", status=204)
        await TadoApi(session, "r").async_resume_room(1, GENERATION_CLASSIC, 2)
        assert any(k[0] == "DELETE" for k in m.requests)


async def test_resume_all_x_uses_quick_action(session):
    with aioresponses() as m:
        m.post(TOKEN_URL, payload=TOKEN)
        m.post(f"{X_API}/homes/1/quickActions/resumeSchedule", status=204)
        await TadoApi(session, "r").async_resume_all(1, GENERATION_X, [1, 2])


async def test_resume_all_classic_iterates(session):
    with aioresponses() as m:
        m.post(TOKEN_URL, payload=TOKEN)
        for zone in (1, 2):
            m.delete(f"{CLASSIC_API}/homes/1/zones/{zone}/overlay", status=204)
        await TadoApi(session, "r").async_resume_all(1, GENERATION_CLASSIC, [1, 2])


async def test_rotated_refresh_token_is_persisted(session):
    saved = []

    async def cb(token):
        saved.append(token)

    with aioresponses() as m:
        m.post(TOKEN_URL, payload=TOKEN)
        m.get(f"{X_API}/homes/1/rooms", payload=[{"id": 1, "name": "Hall"}])
        rooms = await TadoApi(session, "r", cb).async_get_rooms(1, GENERATION_X)
    assert rooms == [{"id": 1, "name": "Hall"}]
    assert saved == ["r2"]


async def test_invalid_refresh_raises_auth_error(session):
    with aioresponses() as m:
        m.post(TOKEN_URL, status=400, payload={"error": "invalid_grant"})
        with pytest.raises(TadoAuthError):
            await TadoApi(session, "bad").async_get_rooms(1, GENERATION_X)


async def test_device_flow_pending(session):
    with aioresponses() as m:
        m.post(TOKEN_URL, status=400, payload={"error": "authorization_pending"})
        with pytest.raises(TadoAuthPending):
            await async_poll_device_flow(session, "code")


async def test_get_state_x_gathers_sections() -> None:
    api = TadoApi(None, "r")
    seen: list[str] = []

    async def fake(method, url, json=None):
        seen.append(url)
        if url.endswith("/rooms"):
            return [{"id": 5}]
        if url.endswith("/state"):
            raise TadoError("nope")
        return {"ok": url.rsplit("/", 1)[-1]}

    api._request = fake
    state = await api.async_get_state(1, "LINE_X")
    assert state["rooms"] == {5: {"id": 5}}
    assert state["presence"] is None
    assert state["weather"] == {"ok": "weather"}
    assert len(seen) == 5


async def test_get_state_classic_merges_zone_state() -> None:
    api = TadoApi(None, "r")

    async def fake(method, url, json=None):
        if url.endswith("/zones"):
            return [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        if url.endswith("/zones/2/state"):
            raise TadoError("nope")
        if url.endswith("/zones/1/state"):
            return {"heatingPower": {"percentage": 10}}
        return {}

    api._request = fake
    state = await api.async_get_state(1, "PRE_LINE_X")
    assert state["rooms"][1]["heatingPower"] == {"percentage": 10}
    assert state["rooms"][2] == {"id": 2, "name": "B"}
