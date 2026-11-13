"""Timed away tests."""

from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.tado_resume.api import TadoError
from custom_components.tado_resume.const import DOMAIN

PRESENCE = "custom_components.tado_resume.TadoApi.async_set_presence"
REFRESH = "custom_components.tado_resume.coordinator.TadoCoordinator.async_request_refresh"


def _api():
    """Patch the read calls so setup and reload never touch the network."""
    stack = ExitStack()
    stack.enter_context(
        patch(
            "custom_components.tado_resume.TadoApi.async_get_rooms",
            AsyncMock(return_value=[{"id": 5, "name": "Hall"}]),
        )
    )
    stack.enter_context(
        patch(
            "custom_components.tado_resume.TadoApi.async_get_state",
            AsyncMock(
                return_value={
                    "rooms": {5: {"id": 5}},
                    "presence": {"presence": "HOME", "presenceLocked": False},
                }
            ),
        )
    )
    return stack


async def _setup(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={"home_id": 1, "generation": "LINE_X", "refresh_token": "r"},
    )
    entry.add_to_hass(hass)
    with _api():
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _call(hass, until):
    await hass.services.async_call(DOMAIN, "set_away_until", {"until": until}, blocking=True)


async def test_away_then_auto(hass):
    entry = await _setup(hass)
    until = dt_util.utcnow() + timedelta(hours=2)
    with patch(PRESENCE, AsyncMock()) as presence, patch(REFRESH, AsyncMock()):
        await _call(hass, until)
        presence.assert_awaited_once_with(1, "LINE_X", "away")
        assert entry.runtime_data.away.until == until
        async_fire_time_changed(hass, until + timedelta(seconds=1))
        await hass.async_block_till_done()
        assert presence.await_args.args == (1, "LINE_X", "auto")
    assert entry.runtime_data.away.until is None


async def test_past_time_rejected(hass):
    await _setup(hass)
    with patch(PRESENCE, AsyncMock()) as presence, pytest.raises(ServiceValidationError):
        await _call(hass, dt_util.utcnow() - timedelta(minutes=1))
    presence.assert_not_awaited()


async def test_set_away_failure(hass):
    entry = await _setup(hass)
    with (
        patch(PRESENCE, AsyncMock(side_effect=TadoError("boom"))),
        pytest.raises(HomeAssistantError),
    ):
        await _call(hass, dt_util.utcnow() + timedelta(hours=1))
    assert entry.runtime_data.away.until is None


async def test_survives_restart(hass):
    entry = await _setup(hass)
    until = dt_util.utcnow() + timedelta(hours=2)
    with patch(PRESENCE, AsyncMock()) as presence, patch(REFRESH, AsyncMock()):
        await _call(hass, until)
        with _api():
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
        assert entry.runtime_data.away.until == until
        presence.reset_mock()
        async_fire_time_changed(hass, until + timedelta(seconds=1))
        await hass.async_block_till_done()
        presence.assert_awaited_once_with(1, "LINE_X", "auto")


async def test_elapsed_while_stopped(hass):
    entry = await _setup(hass)
    until = dt_util.utcnow() + timedelta(hours=2)
    with patch(PRESENCE, AsyncMock()) as presence, patch(REFRESH, AsyncMock()):
        await _call(hass, until)
        await hass.config_entries.async_unload(entry.entry_id)
        presence.reset_mock()
        with (
            _api(),
            patch("homeassistant.util.dt.utcnow", return_value=until + timedelta(hours=1)),
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        presence.assert_awaited_once_with(1, "LINE_X", "auto")
    assert entry.runtime_data.away.until is None


async def test_retry_when_return_fails(hass):
    entry = await _setup(hass)
    until = dt_util.utcnow() + timedelta(hours=1)
    with patch(PRESENCE, AsyncMock()) as presence, patch(REFRESH, AsyncMock()):
        await _call(hass, until)
        presence.side_effect = TadoError("down")
        async_fire_time_changed(hass, until + timedelta(seconds=1))
        await hass.async_block_till_done()
        assert entry.runtime_data.away.until == until
        presence.side_effect = None
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
        await hass.async_block_till_done()
        assert presence.await_args.args == (1, "LINE_X", "auto")
    assert entry.runtime_data.away.until is None


async def test_manual_presence_cancels(hass):
    entry = await _setup(hass)
    with patch(PRESENCE, AsyncMock()), patch(REFRESH, AsyncMock()):
        await _call(hass, dt_util.utcnow() + timedelta(hours=2))
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.tado_home_presence", "option": "home"},
            blocking=True,
        )
    assert entry.runtime_data.away.until is None
