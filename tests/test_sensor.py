"""Sensor and binary sensor tests."""

from unittest.mock import AsyncMock, patch

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.const import DOMAIN
from custom_components.tado_resume.devices import parse_devices

ROOM = {
    "id": 5,
    "name": "Hall",
    "sensorDataPoints": {
        "insideTemperature": {"value": 19.5},
        "humidity": {"percentage": 48},
    },
    "setting": {"power": "ON", "temperature": {"value": 20.0}},
    "heatingPower": {"percentage": 40},
}
DEVICES_X = {
    "rooms": [
        {
            "roomId": 5,
            "devices": [
                {
                    "serialNumber": "RU1",
                    "type": "RU02",
                    "firmwareVersion": "243.1",
                    "connection": {"state": "CONNECTED"},
                    "batteryState": "LOW",
                }
            ],
        }
    ],
    "unassignedDevices": [{"serialNumber": "IB1", "type": "IB02"}],
}


async def _setup(hass, room, devices, generation="LINE_X"):
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
        AsyncMock(return_value={"rooms": {5: room}, "devices": devices}),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _unique_ids(hass):
    return {e.unique_id for e in er.async_get(hass).entities.values()}


async def test_x_entities(hass) -> None:
    await _setup(hass, ROOM, DEVICES_X)
    ids = _unique_ids(hass)
    assert {"1_5_heating_power", "1_5_humidity", "1_RU1_firmware",
            "1_RU1_low_battery", "1_RU1_connectivity"} <= ids
    assert not any(i.startswith("1_IB1") for i in ids)
    assert hass.states.get("sensor.hall_heating_power").state == "40.0"
    assert hass.states.get("sensor.hall_humidity").state == "48.0"
    battery = next(
        s for s in hass.states.async_all("binary_sensor") if "battery" in s.entity_id
    )
    assert battery.state == "on"
    conn = next(
        s for s in hass.states.async_all("binary_sensor") if "connectivity" in s.entity_id
    )
    assert conn.state == "on"


async def test_classic_devices(hass) -> None:
    devices = [
        {
            "serialNo": "VA1",
            "deviceType": "VA02",
            "currentFwVersion": "54.20",
            "connectionState": {"value": False},
            "batteryState": "NORMAL",
        }
    ]
    await _setup(hass, ROOM, devices, "PRE_LINE_X")
    assert {"1_VA1_firmware", "1_VA1_low_battery", "1_VA1_connectivity"} <= _unique_ids(hass)


async def test_no_data_no_entities(hass) -> None:
    await _setup(hass, {"id": 5, "name": "Hall", "setting": {"power": "ON"}}, None)
    ids = _unique_ids(hass)
    assert not any(i.endswith(("heating_power", "humidity", "firmware", "low_battery", "connectivity")) for i in ids)


def test_parse_devices_flat_without_optional_fields() -> None:
    (device,) = parse_devices([{"serialNumber": "X"}])
    assert device["battery_low"] is None and device["connected"] is None
    assert parse_devices(None) == []
