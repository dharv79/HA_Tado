"""Whole-home quick actions and weather tests."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.api import TadoApi, TadoError
from custom_components.tado_resume.const import DOMAIN

WEATHER = {
    "outsideTemperature": {"celsius": 7.5},
    "solarIntensity": {"percentage": 40.0},
    "weatherState": {"value": "CLOUDY"},
}


async def _setup(hass, generation="LINE_X", weather=WEATHER):
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
            AsyncMock(return_value={"rooms": {5: {"id": 5}}, "weather": weather}),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_weather_sensors(hass):
    await _setup(hass)
    ids = {e.unique_id for e in er.async_get(hass).entities.values()}
    assert {"1_weather_outsideTemperature", "1_weather_solarIntensity"} <= ids
    assert hass.states.get("sensor.tado_home_outside_temperature").state == "7.5"
    assert hass.states.get("sensor.tado_home_solar_intensity").state == "40.0"
    assert hass.states.get("sensor.tado_home_weather").state == "cloudy"


async def test_no_weather(hass):
    await _setup(hass, weather=None)
    ids = {e.unique_id for e in er.async_get(hass).entities.values()}
    assert not {i for i in ids if "weather" in i}


async def test_boost_button_only_on_x(hass):
    await _setup(hass, generation="PRE_LINE_X")
    ids = {e.unique_id for e in er.async_get(hass).entities.values()}
    assert "1_home_turn_off_all" in ids
    assert "1_home_boost_all" not in ids


async def test_button_and_service(hass):
    await _setup(hass)
    with (
        patch("custom_components.tado_resume.TadoApi.async_boost_all", AsyncMock()) as boost,
        patch(
            "custom_components.tado_resume.coordinator.TadoCoordinator.async_request_refresh",
            AsyncMock(),
        ),
    ):
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.tado_home_boost_all_rooms"},
            blocking=True,
        )
        await hass.services.async_call(DOMAIN, "boost_all_rooms", blocking=True)
    assert boost.await_count == 2
    boost.assert_awaited_with(1, "LINE_X", [5])


@pytest.mark.parametrize(
    ("method", "path"),
    [("async_boost_all", "boost"), ("async_turn_off_all", "turnOffAll")],
)
async def test_x_quick_action_request(method, path):
    api = TadoApi(None, "r")
    api._request = AsyncMock()
    await getattr(api, method)(1, "LINE_X", [5])
    api._request.assert_awaited_once_with(
        "POST", f"https://hops.tado.com/homes/1/quickActions/{path}"
    )


async def test_classic_turn_off_all_and_boost():
    api = TadoApi(None, "r")
    api.async_set_manual = AsyncMock()
    await api.async_turn_off_all(1, "PRE_LINE_X", [5, 6])
    assert api.async_set_manual.await_count == 2
    api.async_set_manual.assert_awaited_with(1, "PRE_LINE_X", 6, None)
    with pytest.raises(TadoError):
        await api.async_boost_all(1, "PRE_LINE_X", [5])
