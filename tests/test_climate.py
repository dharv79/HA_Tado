"""Climate entity and API write tests."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.api import TadoApi, TadoError
from custom_components.tado_resume.const import DOMAIN

ROOM_X = {
    "id": 5,
    "name": "Hall",
    "sensorDataPoints": {
        "insideTemperature": {"value": 19.5},
        "humidity": {"percentage": 48},
    },
    "setting": {"power": "ON", "temperature": {"value": 20.0}},
    "heatingPower": {"percentage": 40},
    "manualControlTermination": None,
}
ENTITY = "climate.hall"


async def _setup(hass, request, room, generation="LINE_X", options=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={"home_id": 1, "generation": generation, "refresh_token": "r"},
        options=options or {},
    )
    entry.add_to_hass(hass)
    refresh = patch(
        "custom_components.tado_resume.TadoCoordinator.async_request_refresh",
        AsyncMock(),
    )
    refresh.start()
    request.addfinalizer(refresh.stop)
    with (
        patch(
            "custom_components.tado_resume.TadoApi.async_get_rooms",
            AsyncMock(return_value=[{"id": 5, "name": "Hall"}]),
        ),
        patch(
            "custom_components.tado_resume.TadoApi.async_get_state",
            AsyncMock(return_value={"rooms": {5: room}}),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_state(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    state = hass.states.get(ENTITY)
    assert state.state == "auto"
    assert state.attributes["current_temperature"] == 19.5
    assert state.attributes["current_humidity"] == 48
    assert state.attributes["temperature"] == 20.0
    assert state.attributes["hvac_action"] == "heating"
    assert state.attributes["preset_mode"] == "schedule"


async def test_off_and_override_states(hass: HomeAssistant, request) -> None:
    room = {**ROOM_X, "setting": {"power": "OFF"}, "manualControlTermination": {}}
    await _setup(hass, request, room)
    state = hass.states.get(ENTITY)
    assert state.state == "off"
    assert state.attributes["hvac_action"] == "off"


async def test_set_temperature(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    with patch("custom_components.tado_resume.TadoApi.async_set_manual", AsyncMock()) as call:
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": ENTITY, "temperature": 21},
            blocking=True,
        )
    call.assert_awaited_once_with(1, "LINE_X", 5, 21.0, "next_schedule_block", None, False)


async def test_set_room_temperature_timer(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    with patch("custom_components.tado_resume.TadoApi.async_set_manual", AsyncMock()) as call:
        await hass.services.async_call(
            DOMAIN,
            "set_room_temperature",
            {
                "entity_id": ENTITY,
                "temperature": 22,
                "termination": "duration",
                "duration": 30,
            },
            blocking=True,
        )
    call.assert_awaited_once_with(1, "LINE_X", 5, 22.0, "duration", 1800, False)


async def test_timer_requires_duration(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "set_room_temperature",
            {"entity_id": ENTITY, "temperature": 22, "termination": "duration"},
            blocking=True,
        )


async def test_hvac_modes_and_boost(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    with (
        patch("custom_components.tado_resume.TadoApi.async_set_manual", AsyncMock()) as manual,
        patch("custom_components.tado_resume.TadoApi.async_resume_room", AsyncMock()) as resume,
        patch("custom_components.tado_resume.TadoApi.async_boost_room", AsyncMock()) as boost,
    ):
        await hass.services.async_call(
            "climate", "set_hvac_mode", {"entity_id": ENTITY, "hvac_mode": "off"}, blocking=True
        )
        manual.assert_awaited_once_with(1, "LINE_X", 5, None, "next_schedule_block", None, False)
        await hass.services.async_call(
            "climate", "set_hvac_mode", {"entity_id": ENTITY, "hvac_mode": "auto"}, blocking=True
        )
        resume.assert_awaited_once_with(1, "LINE_X", 5)
        await hass.services.async_call(
            "climate",
            "set_preset_mode",
            {"entity_id": ENTITY, "preset_mode": "boost"},
            blocking=True,
        )
        boost.assert_awaited_once_with(1, "LINE_X", 5, 25.0, 1800)


async def test_api_error_raises(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    with (
        patch(
            "custom_components.tado_resume.TadoApi.async_set_manual",
            AsyncMock(side_effect=TadoError("boom")),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            "climate", "set_temperature", {"entity_id": ENTITY, "temperature": 21}, blocking=True
        )


async def test_classic_has_no_presets(hass: HomeAssistant, request) -> None:
    room = {
        "id": 5,
        "setting": {"type": "HEATING", "power": "ON", "temperature": {"celsius": 19.0}},
        "overlay": None,
        "activityDataPoints": {"heatingPower": {"percentage": 0}},
    }
    await _setup(hass, request, room, "PRE_LINE_X")
    state = hass.states.get(ENTITY)
    assert state.attributes["hvac_action"] == "idle"
    assert "preset_modes" not in state.attributes


def _api(calls):
    api = TadoApi(None, "r")

    async def fake(method, url, json=None):
        calls.append((method, url, json))

    api._request = fake
    return api


@pytest.mark.parametrize(
    ("termination", "duration", "expected"),
    [
        ("next_schedule_block", None, {"type": "NEXT_TIME_BLOCK"}),
        ("duration", 600, {"type": "TIMER", "durationInSeconds": "600"}),
        ("indefinite", None, {"type": "MANUAL"}),
    ],
)
async def test_api_x_terminations(termination, duration, expected) -> None:
    calls = []
    await _api(calls).async_set_manual(1, "LINE_X", 5, 21.0, termination, duration)
    method, url, body = calls[0]
    assert (method, url) == ("POST", "https://hops.tado.com/homes/1/rooms/5/manualControl")
    assert body["termination"] == expected
    assert body["setting"] == {
        "power": "ON",
        "isBoost": "False",
        "temperature": {"value": "21.0"},
    }


async def test_api_x_off_and_boost() -> None:
    calls = []
    api = _api(calls)
    await api.async_set_manual(1, "LINE_X", 5, None)
    assert calls[0][2]["setting"] == {"power": "OFF"}
    await api.async_boost_room(1, "LINE_X", 5)
    body = calls[1][2]
    assert body["setting"]["isBoost"] == "True"
    assert body["termination"] == {"type": "TIMER", "durationInSeconds": "1800"}


@pytest.mark.parametrize(
    ("termination", "duration", "expected"),
    [
        ("next_schedule_block", None, {"typeSkillBasedApp": "TADO_MODE"}),
        ("duration", 600, {"typeSkillBasedApp": "TIMER", "durationInSeconds": 600}),
        ("indefinite", None, {"typeSkillBasedApp": "MANUAL"}),
    ],
)
async def test_api_classic_overlay(termination, duration, expected) -> None:
    calls = []
    await _api(calls).async_set_manual(1, "PRE_LINE_X", 5, 21.0, termination, duration)
    method, url, body = calls[0]
    assert (method, url) == ("PUT", "https://my.tado.com/api/v2/homes/1/zones/5/overlay")
    assert body["termination"] == expected
    assert body["setting"]["temperature"] == {"celsius": 21.0}


async def test_api_validation_errors() -> None:
    api = _api([])
    with pytest.raises(TadoError):
        await api.async_set_manual(1, "LINE_X", 5, 21.0, "duration", None)
    with pytest.raises(TadoError):
        await api.async_set_manual(1, "LINE_X", 5, 21.0, "bogus")
    with pytest.raises(TadoError):
        await api.async_boost_room(1, "PRE_LINE_X", 5)
