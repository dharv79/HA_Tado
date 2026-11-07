"""Presence, open-window sensor and device tracker tests."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.api import TadoApi
from custom_components.tado_resume.const import DOMAIN

ROOM = {"id": 5, "name": "Hall", "openWindow": {"expiryInSeconds": 100}}
MOBILE = [
    {"id": 1, "name": "Phone", "settings": {"geoTrackingEnabled": True},
     "location": {"atHome": True}},
    {"id": 2, "name": "Tablet", "settings": {"geoTrackingEnabled": False}},
]


async def _setup(hass, state, generation="LINE_X"):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={"home_id": 1, "generation": generation, "refresh_token": "r"},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.tado_resume.TadoApi.async_get_rooms",
        AsyncMock(return_value=[{"id": 5, "name": "Hall"}]),
    ), patch(
        "custom_components.tado_resume.TadoApi.async_get_state",
        AsyncMock(return_value={"rooms": {5: ROOM}, **state}),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_entities(hass):
    await _setup(
        hass,
        {
            "presence": {"presence": "HOME", "presenceLocked": False},
            "mobile_devices": MOBILE,
        },
    )
    ids = {e.unique_id for e in er.async_get(hass).entities.values()}
    assert "1_presence" in ids
    assert "1_5_open_window" in ids
    assert not {i for i in ids if i.endswith(("_activate", "_reset"))}
    assert "1_mobile_1" in ids
    assert "1_mobile_2" not in ids
    assert hass.states.get("select.tado_home_presence").state == "auto"
    assert hass.states.get("binary_sensor.hall_open_window").state == "on"
    assert hass.states.get("device_tracker.phone").state == "home"


async def test_nothing_without_data(hass):
    await _setup(hass, {})
    ids = {e.unique_id for e in er.async_get(hass).entities.values()}
    assert not {i for i in ids if "presence" in i or "mobile" in i}


async def test_select_presence(hass):
    await _setup(hass, {"presence": {"presence": "AWAY", "presenceLocked": True}})
    assert hass.states.get("select.tado_home_presence").state == "away"
    with patch(
        "custom_components.tado_resume.TadoApi.async_set_presence", AsyncMock()
    ) as call, patch(
        "custom_components.tado_resume.coordinator.TadoCoordinator.async_request_refresh",
        AsyncMock(),
    ):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.tado_home_presence", "option": "home"},
            blocking=True,
        )
    call.assert_awaited_once_with(1, "LINE_X", "home")


@pytest.mark.parametrize(
    ("generation", "presence", "expected"),
    [
        ("LINE_X", "auto", ("PUT", "https://hops.tado.com/homes/1/presence", {"homePresence": "AUTO"})),
        ("LINE_X", "away", ("PUT", "https://hops.tado.com/homes/1/presence", {"homePresence": "AWAY"})),
        ("PRE_LINE_X", "home", ("PUT", "https://my.tado.com/api/v2/homes/1/presenceLock", {"homePresence": "HOME"})),
        ("PRE_LINE_X", "auto", ("DELETE", "https://my.tado.com/api/v2/homes/1/presenceLock")),
    ],
)
async def test_presence_requests(generation, presence, expected):
    api = TadoApi(None, "r")
    api._request = AsyncMock()
    await api.async_set_presence(1, generation, presence)
    api._request.assert_awaited_once_with(*expected)


async def test_legacy_open_window_buttons_removed(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={"home_id": 1, "generation": "LINE_X", "refresh_token": "r"},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "button", DOMAIN, "1_5_open_window_activate", config_entry=entry
    )
    with patch(
        "custom_components.tado_resume.TadoApi.async_get_rooms",
        AsyncMock(return_value=[{"id": 5, "name": "Hall"}]),
    ), patch(
        "custom_components.tado_resume.TadoApi.async_get_state",
        AsyncMock(return_value={"rooms": {5: ROOM}}),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert registry.async_get_entity_id("button", DOMAIN, "1_5_open_window_activate") is None
