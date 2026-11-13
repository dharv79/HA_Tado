"""Heating run-time read and sensor (Phase 7)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.api import TadoApi, TadoAuthError, TadoError
from custom_components.tado_resume.const import DOMAIN

PAYLOAD = {
    "runningTimes": [
        {
            "runningTimeInSeconds": 3600,
            "zones": [
                {"id": 1, "runningTimeInSeconds": 2400},
                {"id": 2, "runningTimeInSeconds": 1200},
            ],
        }
    ]
}


async def test_run_time_parsed_and_cached() -> None:
    api = TadoApi(None, "r")
    calls = []

    async def fake(method, url, json=None):
        calls.append(url)
        return PAYLOAD

    api._request = fake
    first = await api._run_time(1)
    assert first == {"seconds": 3600, "zones": {1: 2400, 2: 1200}}
    assert "minder.tado.com/v1/homes/1/runningTimes?from=" in calls[0]
    await api._run_time(1)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "payload", [None, {}, {"runningTimes": "x"}, {"runningTimes": [{"zones": [{}]}]}]
)
async def test_run_time_unavailable_or_malformed(payload) -> None:
    api = TadoApi(None, "r")

    async def fake(method, url, json=None):
        if payload is None:
            raise TadoError("nope")
        return payload

    api._request = fake
    assert await api._run_time(1) is None


async def test_run_time_auth_error_propagates() -> None:
    api = TadoApi(None, "r")

    async def fake(method, url, json=None):
        raise TadoAuthError("expired")

    api._request = fake
    with pytest.raises(TadoAuthError):
        await api._run_time(1)


async def test_state_run_time_classic_only() -> None:
    api = TadoApi(None, "r")
    urls = []

    async def fake(method, url, json=None):
        urls.append(url)
        if url.endswith("/zones") or url.endswith("/rooms"):
            return []
        if "runningTimes" in url:
            return PAYLOAD
        return {}

    api._request = fake
    assert (await api.async_get_state(1, "PRE_LINE_X"))["run_time"]["seconds"] == 3600
    urls.clear()
    assert (await api.async_get_state(1, "LINE_X"))["run_time"] is None
    assert not any("runningTimes" in u for u in urls)


@pytest.mark.parametrize("run_time", [{"seconds": 5400, "zones": {1: 5400}}, None])
async def test_sensor_created_only_with_data(hass, run_time) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={"home_id": 1, "generation": "PRE_LINE_X", "refresh_token": "r"},
    )
    entry.add_to_hass(hass)
    state = {"rooms": {}, "devices": None, "run_time": run_time}
    with (
        patch("custom_components.tado_resume.TadoApi.async_get_rooms", AsyncMock(return_value=[])),
        patch(
            "custom_components.tado_resume.TadoApi.async_get_state", AsyncMock(return_value=state)
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    eid = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "1_heating_run_time")
    if run_time is None:
        assert eid is None
        return
    assert float(hass.states.get(eid).state) == 1.5
    assert hass.states.get(eid).attributes["zones"] == {1: 5400}
