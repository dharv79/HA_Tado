"""Device settings: temperature offset and child lock."""

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aioresponses import aioresponses
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.api import (
    CLASSIC_API,
    GENERATION_CLASSIC,
    GENERATION_X,
    TOKEN_URL,
    X_API,
    TadoApi,
    TadoError,
)
from custom_components.tado_resume.const import DOMAIN
from custom_components.tado_resume.devices import parse_devices

TOKEN = {"access_token": "a", "refresh_token": "r2", "expires_in": 600}
ROOM = {"id": 5, "name": "Hall", "setting": {"power": "ON"}}
DEVICES_X = {
    "rooms": [
        {
            "roomId": 5,
            "devices": [
                {
                    "serialNumber": "RU1",
                    "type": "RU02",
                    "temperatureOffset": 0.5,
                    "childLockEnabled": False,
                }
            ],
        }
    ],
    "unassignedDevices": [{"serialNumber": "IB1", "type": "IB02"}],
}


async def _setup(hass, devices, generation="LINE_X"):
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
            AsyncMock(return_value={"rooms": {5: ROOM}, "devices": devices}),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _ids(hass):
    return {e.unique_id for e in er.async_get(hass).entities.values()}


def test_parse_offset_and_child_lock() -> None:
    (a,) = parse_devices([{"serialNo": "A", "temperatureOffset": {"celsius": -1.5}}])
    (b,) = parse_devices([{"serialNo": "B", "temperatureOffset": True, "childLockEnabled": 1}])
    (c,) = parse_devices([{"serialNo": "C", "childLockEnabled": True}])
    assert a["temperature_offset"] == -1.5 and a["child_lock"] is None
    assert b["temperature_offset"] is None and b["child_lock"] is None
    assert c["child_lock"] is True


async def test_entities_only_where_reported(hass) -> None:
    await _setup(hass, DEVICES_X)
    ids = _ids(hass)
    assert {"1_RU1_temperature_offset", "1_RU1_child_lock"} <= ids
    assert not any(i.startswith("1_IB1") for i in ids)
    assert hass.states.get("number.tado_ru02_ru1_temperature_offset").state == "0.5"
    assert hass.states.get("switch.tado_ru02_ru1_child_lock").state == "off"


async def test_classic_has_child_lock_but_no_offset(hass) -> None:
    devices = [{"serialNo": "VA1", "temperatureOffset": 1.0, "childLockEnabled": True}]
    await _setup(hass, devices, "PRE_LINE_X")
    ids = _ids(hass)
    assert "1_VA1_child_lock" in ids
    assert "1_VA1_temperature_offset" not in ids


async def test_writes_call_api_and_refresh(hass) -> None:
    await _setup(hass, DEVICES_X)
    with (
        patch(
            "custom_components.tado_resume.TadoApi.async_set_temperature_offset", AsyncMock()
        ) as offset,
        patch("custom_components.tado_resume.TadoApi.async_set_child_lock", AsyncMock()) as lock,
        patch(
            "custom_components.tado_resume.TadoApi.async_get_state",
            AsyncMock(return_value={"rooms": {5: ROOM}, "devices": DEVICES_X}),
        ),
    ):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.tado_ru02_ru1_temperature_offset", "value": -1.25},
            blocking=True,
        )
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.tado_ru02_ru1_child_lock"}, blocking=True
        )
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": "switch.tado_ru02_ru1_child_lock"}, blocking=True
        )
    offset.assert_awaited_once_with(1, "LINE_X", "RU1", -1.2)
    assert [c.args[-1] for c in lock.await_args_list] == [True, False]


async def test_out_of_range_offset_rejected(hass) -> None:
    await _setup(hass, DEVICES_X)
    with pytest.raises(ServiceValidationError, match="outside valid range"):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.tado_ru02_ru1_temperature_offset", "value": 11},
            blocking=True,
        )


async def test_write_failure_is_reported(hass) -> None:
    await _setup(hass, DEVICES_X)
    with (
        patch(
            "custom_components.tado_resume.TadoApi.async_set_child_lock",
            AsyncMock(side_effect=TadoError("nope")),
        ),
        pytest.raises(HomeAssistantError, match="Child lock change failed"),
    ):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.tado_ru02_ru1_child_lock"}, blocking=True
        )


async def test_api_endpoints() -> None:
    async with aiohttp.ClientSession() as session:
        api = TadoApi(session, "r")
        device = f"{X_API}/homes/1/roomsAndDevices/devices/RU1"
        with aioresponses() as m:
            m.post(TOKEN_URL, payload=TOKEN)
            m.patch(device, status=204)
            m.patch(device, status=204)
            m.put(f"{CLASSIC_API}/devices/VA1/childLock", status=204)
            await api.async_set_temperature_offset(1, GENERATION_X, "RU1", 0.5)
            await api.async_set_child_lock(1, GENERATION_X, "RU1", True)
            await api.async_set_child_lock(1, GENERATION_CLASSIC, "VA1", False)
            bodies = [
                call.kwargs["json"]
                for key, calls in m.requests.items()
                if key[0] != "POST"
                for call in calls
            ]
        assert {"temperatureOffset": 0.5} in bodies
        assert {"childLockEnabled": True} in bodies
        assert {"childLockEnabled": False} in bodies
        with pytest.raises(TadoError):
            await api.async_set_temperature_offset(1, GENERATION_CLASSIC, "VA1", 0.5)
