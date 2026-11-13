"""Schedule sensors (read-only, classic)."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.api import CLASSIC_API, TadoApi, TadoError
from custom_components.tado_resume.const import DOMAIN
from custom_components.tado_resume.schedule import day_type, next_change

LONDON = ZoneInfo("Europe/London")


def _block(day, start, temp, power="ON"):
    return {
        "dayType": day,
        "start": start,
        "end": "00:00",
        "setting": {"power": power, "temperature": {"celsius": temp}},
    }


THREE = {
    "type": "THREE_DAY",
    "blocks": [
        _block("MONDAY_TO_FRIDAY", "00:00", 16),
        _block("MONDAY_TO_FRIDAY", "07:00", 21),
        _block("MONDAY_TO_FRIDAY", "22:00", 16),
        _block("SATURDAY", "00:00", 16),
        _block("SATURDAY", "09:00", 21),
        _block("SUNDAY", "00:00", 16, "OFF"),
    ],
}


def test_day_type() -> None:
    assert day_type("ONE_DAY", 3) == "MONDAY_TO_SUNDAY"
    assert day_type("THREE_DAY", 4) == "MONDAY_TO_FRIDAY"
    assert day_type("THREE_DAY", 6) == "SUNDAY"
    assert day_type("SEVEN_DAY", 2) == "WEDNESDAY"


def test_next_change_same_day_and_rollover() -> None:
    mon_early = datetime(2026, 11, 9, 6, 0, tzinfo=LONDON)  # Monday
    nxt = next_change(THREE, mon_early)
    assert nxt["at"] == datetime(2026, 11, 9, 7, 0, tzinfo=LONDON)
    assert nxt["temperature"] == 21
    fri_late = datetime(2026, 11, 13, 23, 0, tzinfo=LONDON)  # Friday night
    nxt = next_change(THREE, fri_late)
    assert nxt["at"] == datetime(2026, 11, 14, 9, 0, tzinfo=LONDON)  # Saturday 09:00


def test_next_change_skips_identical_and_reports_off() -> None:
    sat_late = datetime(2026, 11, 14, 12, 0, tzinfo=LONDON)
    nxt = next_change(THREE, sat_late)
    # Saturday 21 -> Sunday 00:00 OFF
    assert nxt["at"] == datetime(2026, 11, 15, 0, 0, tzinfo=LONDON)
    assert nxt["power"] == "OFF"


def test_next_change_invalid_input() -> None:
    now = datetime(2026, 11, 9, 6, 0, tzinfo=LONDON)
    assert next_change(None, now) is None
    assert next_change({"type": "ONE_DAY", "blocks": "x"}, now) is None
    flat = {"type": "ONE_DAY", "blocks": [_block("MONDAY_TO_SUNDAY", "00:00", 20), {"x": 1}]}
    assert next_change(flat, now) is None


async def test_api_schedule_cached_and_failure_tolerated() -> None:
    api = TadoApi(None, "r")
    calls: list[str] = []

    async def fake(method, url, json=None):
        calls.append(url)
        if url.endswith("activeTimetable"):
            return {"id": 2, "type": "ONE_DAY"}
        return [_block("MONDAY_TO_SUNDAY", "00:00", 20)]

    api._request = fake
    first = await api._schedule(1, 7)
    assert first["type"] == "ONE_DAY"
    assert calls[1] == f"{CLASSIC_API}/homes/1/zones/7/schedule/timetables/2/blocks"
    await api._schedule(1, 7)
    assert len(calls) == 2  # cached

    async def broken(method, url, json=None):
        raise TadoError("nope")

    api._request = broken
    assert await api._schedule(1, 8) is None


async def test_classic_state_includes_schedule() -> None:
    api = TadoApi(None, "r")

    async def fake(method, url, json=None):
        if url.endswith("/zones"):
            return [{"id": 1, "name": "A"}]
        if url.endswith("activeTimetable"):
            return {"id": 0, "type": "ONE_DAY"}
        if url.endswith("/blocks"):
            return []
        return {}

    api._request = fake
    state = await api.async_get_state(1, "PRE_LINE_X")
    assert state["rooms"][1]["schedule"] == {"type": "ONE_DAY", "blocks": []}


@pytest.mark.parametrize("with_schedule", [True, False])
async def test_sensors_created_only_with_schedule(hass, with_schedule) -> None:
    room = {"id": 5, "name": "Hall", "setting": {"power": "ON"}}
    if with_schedule:
        room["schedule"] = {
            "type": "ONE_DAY",
            "blocks": [
                _block("MONDAY_TO_SUNDAY", "00:00", 16),
                _block("MONDAY_TO_SUNDAY", "07:00", 21),
            ],
        }
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={"home_id": 1, "generation": "PRE_LINE_X", "refresh_token": "r"},
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
    reg = er.async_get(hass)
    change = reg.async_get_entity_id("sensor", DOMAIN, "1_5_next_schedule_change")
    temp = reg.async_get_entity_id("sensor", DOMAIN, "1_5_next_schedule_temperature")
    if not with_schedule:
        assert change is None and temp is None
        return
    assert datetime.fromisoformat(hass.states.get(change).state).tzinfo is not None
    assert float(hass.states.get(temp).state) in (16.0, 21.0)
