"""Override details sensors."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.const import DOMAIN
from custom_components.tado_resume.entity import override_termination

BASE = {"id": 5, "name": "Hall", "setting": {"power": "ON"}}


def test_parse_x_timer_and_manual() -> None:
    room = {**BASE, "manualControlTermination": {"type": "TIMER", "remainingTimeInSeconds": 90}}
    assert override_termination(room) == {"type": "timer", "remaining": 90, "expiry": None}
    room = {**BASE, "manualControlTermination": {"type": "MANUAL"}}
    assert override_termination(room)["type"] == "manual"
    assert override_termination({**BASE, "manualControlTermination": None}) is None


def test_parse_classic_overlay() -> None:
    room = {
        **BASE,
        "overlay": {
            "termination": {
                "typeSkillBasedApp": "TADO_MODE",
                "projectedExpiry": "2026-01-01T10:00:00Z",
                "remainingTimeInSeconds": 60,
            }
        },
    }
    info = override_termination(room)
    assert info == {
        "type": "next_schedule_block",
        "remaining": 60,
        "expiry": "2026-01-01T10:00:00Z",
    }
    assert override_termination({**BASE, "overlay": None}) is None


async def _setup(hass, room, generation="LINE_X"):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={"home_id": 1, "generation": generation, "refresh_token": "r"},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.tado_resume.TadoApi.async_get_rooms",
            AsyncMock(return_value=[{"id": 5, "name": "Hall"}]),
        ),
        patch(
            "custom_components.tado_resume.TadoApi.async_get_state",
            AsyncMock(return_value={"rooms": {5: room}, "devices": None}),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _entity(hass, key):
    reg = er.async_get(hass)
    eid = reg.async_get_entity_id("sensor", DOMAIN, f"1_5_{key}")
    return hass.states.get(eid) if eid else None


async def test_timer_override_x(hass) -> None:
    room = {**BASE, "manualControlTermination": {"type": "TIMER", "remainingTimeInSeconds": 900}}
    await _setup(hass, room)
    assert float(_entity(hass, "override_remaining").state) == 15  # shown in minutes
    ends = _entity(hass, "override_ends")
    assert ends.attributes["termination"] == "timer"
    assert datetime.fromisoformat(ends.state).tzinfo is not None


async def test_classic_expiry_used_and_manual_unknown(hass) -> None:
    room = {
        **BASE,
        "overlay": {"termination": {"type": "TIMER", "expiry": "2026-01-01T10:00:00Z"}},
    }
    await _setup(hass, room, "PRE_LINE_X")
    ends = _entity(hass, "override_ends")
    assert datetime.fromisoformat(ends.state) == datetime(2026, 1, 1, 10, tzinfo=UTC)
    assert _entity(hass, "override_remaining").state == "unknown"


async def test_no_override_is_unknown(hass) -> None:
    await _setup(hass, {**BASE, "manualControlTermination": None})
    assert _entity(hass, "override_ends").state == "unknown"
    assert _entity(hass, "override_ends").attributes["termination"] is None
