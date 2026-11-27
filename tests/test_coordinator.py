"""Coordinator, capability and diagnostics tests (fixtures are illustrative)."""

import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.api import TadoAuthError, TadoError, TadoRateLimitError
from custom_components.tado_resume.capabilities import room_capabilities
from custom_components.tado_resume.const import DEFAULT_POLL_INTERVAL, DOMAIN
from custom_components.tado_resume.coordinator import MAX_INTERVAL
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
    with (
        patch(
            "custom_components.tado_resume.TadoApi.async_get_rooms",
            AsyncMock(return_value=[{"id": 5, "name": "Hall"}]),
        ),
        patch(
            "custom_components.tado_resume.TadoApi.async_get_state",
            AsyncMock(return_value=state),
        ),
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
    with patch.object(coordinator.api, "async_get_state", AsyncMock(side_effect=TadoError("x"))):
        for _ in range(10):
            await coordinator.async_refresh()
    assert coordinator.update_interval == MAX_INTERVAL
    with patch.object(coordinator.api, "async_get_state", AsyncMock(return_value=STATE)):
        await coordinator.async_refresh()
    assert coordinator.update_interval == timedelta(seconds=DEFAULT_POLL_INTERVAL)


async def test_auth_error_raises_auth_failed(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    with (
        patch.object(coordinator.api, "async_get_state", AsyncMock(side_effect=TadoAuthError("x"))),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()


async def test_diagnostics_redacted(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    text = json.dumps(await async_get_config_entry_diagnostics(hass, entry))
    for secret in ("secret-r", "RU0000000000", "Phone", "Hall"):
        assert secret not in text


async def test_repair_issue_after_sustained_failure(hass: HomeAssistant) -> None:
    from datetime import timedelta

    from homeassistant.helpers import issue_registry as ir
    from homeassistant.util import dt as dt_util

    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    registry = ir.async_get(hass)
    issue_id = "api_unreachable_1"
    start = dt_util.utcnow()
    with patch.object(coordinator.api, "async_get_state", AsyncMock(side_effect=TadoError("x"))):
        await coordinator.async_refresh()
        assert registry.async_get_issue(DOMAIN, issue_id) is None
        with patch(
            "custom_components.tado_resume.coordinator.dt_util.utcnow",
            return_value=start + timedelta(hours=1, minutes=1),
        ):
            await coordinator.async_refresh()
        assert registry.async_get_issue(DOMAIN, issue_id) is not None
    with patch.object(coordinator.api, "async_get_state", AsyncMock(return_value=STATE)):
        await coordinator.async_refresh()
    assert registry.async_get_issue(DOMAIN, issue_id) is None
    assert coordinator.last_success is not None


async def test_last_update_sensor_stays_available(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    state = hass.states.get("sensor.tado_home_last_successful_update")
    assert state is not None and state.state != "unavailable"
    with patch.object(coordinator.api, "async_get_state", AsyncMock(side_effect=TadoError("x"))):
        await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.tado_home_last_successful_update").state != "unavailable"


async def test_away_home_polls_slower_and_rate_limit_is_honoured(hass: HomeAssistant) -> None:
    away = {**STATE, "presence": {"presence": "AWAY"}}
    entry = await _setup(hass, away)
    coordinator = entry.runtime_data.coordinator
    base = timedelta(seconds=DEFAULT_POLL_INTERVAL)
    assert coordinator.update_interval == base * 3

    with patch.object(
        coordinator.api, "async_get_state", AsyncMock(side_effect=TadoRateLimitError("x", 600))
    ):
        await coordinator.async_refresh()
    assert coordinator.update_interval == timedelta(seconds=600)

    with patch.object(coordinator.api, "async_get_state", AsyncMock(return_value=STATE)):
        await coordinator.async_refresh()
    assert coordinator.update_interval == base


async def test_rate_limit_raises_issue_and_waits(hass: HomeAssistant) -> None:
    from homeassistant.helpers import issue_registry as ir

    from custom_components.tado_resume.coordinator import RATE_LIMIT_WAIT

    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    registry = ir.async_get(hass)
    with patch.object(
        coordinator.api, "async_get_state", AsyncMock(side_effect=TadoRateLimitError("x"))
    ):
        await coordinator.async_refresh()
    assert coordinator.update_interval == RATE_LIMIT_WAIT
    issue = registry.async_get_issue(DOMAIN, "rate_limited_1")
    assert issue is not None and issue.translation_placeholders["time"]
    assert registry.async_get_issue(DOMAIN, "api_unreachable_1") is None
    with patch.object(coordinator.api, "async_get_state", AsyncMock(return_value=STATE)):
        await coordinator.async_refresh()
    assert registry.async_get_issue(DOMAIN, "rate_limited_1") is None


async def test_polling_is_paced_to_quota(hass: HomeAssistant) -> None:
    import time

    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    api = coordinator.api
    base = timedelta(seconds=DEFAULT_POLL_INTERVAL)

    async def poll(remaining, refill_in, used):
        async def fake(*_):
            api.request_count += used
            api.quota_remaining = remaining
            api.quota_refill_at = time.time() + refill_in if refill_in else None
            return STATE

        with patch.object(api, "async_get_state", fake):
            await coordinator.async_refresh()
        return coordinator.update_interval

    # Plenty left: steady interval.
    assert await poll(19000, None, 2) == base
    coordinator._per_poll = None
    # 90 left (80 spare) for 8 h at 2 per poll: 2 * 28800 / 80 = 720 s.
    interval = await poll(90, 28800, 2)
    assert abs(interval.total_seconds() - 720) < 5
    # Nothing spare: wait until the refill.
    interval = await poll(5, 3000, 2)
    assert abs(interval.total_seconds() - 3000) < 5
    # Nothing spare and no refill time: capped.
    from custom_components.tado_resume.coordinator import MAX_PACED_INTERVAL

    assert await poll(5, None, 2) == MAX_PACED_INTERVAL


async def test_requests_remaining_sensor(hass: HomeAssistant) -> None:
    import time

    entry = await _setup(hass)
    coordinator = entry.runtime_data.coordinator
    coordinator.api.quota_remaining = 57
    coordinator.api.quota_refill_at = time.time() + 600
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    state = hass.states.get("sensor.tado_home_tado_requests_remaining")
    assert state.state == "57"
    assert "refills_at" in state.attributes
