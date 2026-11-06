"""Coordinator, capability and diagnostics tests (fixtures are illustrative)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.api import TadoAuthError, TadoError
from custom_components.tado_resume.capabilities import room_capabilities
from custom_components.tado_resume.const import DOMAIN
from custom_components.tado_resume.coordinator import BASE_INTERVAL, MAX_INTERVAL
from custom_components.tado_resume.diagnostics import async_get_config_entry_diagnostics

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "state_x.json").read_text())
STATE = {**FIXTURE, "rooms": {int(k): v for k, v in FIXTURE["rooms"].items()}}


async def _setup(hass: HomeAssistant, state=STATE):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={"home_id": 1, "generation": "LINE_X", "refresh_token": "secret-r"},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.tado_resume.TadoApi.async_get_rooms",
        AsyncMock(return_value=[{"id": 5, "name": "Hall"}]),
    ), patch(
        "custom_components.tado_resume.TadoApi.async_get_state",
        AsyncMock(return_value=state),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_coordinator_populates_from_fixture(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    assert coordinator.data["presence"] == {"presence": "HOME"}
    assert {"resume", "temperature", "humidity", "heating_power", "override"} <= (
        coordinator.capabilities[5]
    )


def test_capabilities_minimal_room() -> None:
    assert room_capabilities({"id": 1}) == {"resume"}


async def test_backoff_and_reset(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    with patch.object(
        coordinator.api, "async_get_state", AsyncMock(side_effect=TadoError("x"))
    ):
        for _ in range(10):
            await coordinator.async_refresh()
    assert coordinator.update_interval == MAX_INTERVAL
    with patch.object(coordinator.api, "async_get_state", AsyncMock(return_value=STATE)):
        await coordinator.async_refresh()
    assert coordinator.update_interval == BASE_INTERVAL


async def test_auth_error_raises_auth_failed(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    with patch.object(
        coordinator.api, "async_get_state", AsyncMock(side_effect=TadoAuthError("x"))
    ), pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_diagnostics_redacted(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    text = json.dumps(await async_get_config_entry_diagnostics(hass, entry))
    for secret in ("secret-r", "RU0000000000", "Phone", "Hall"):
        assert secret not in text
