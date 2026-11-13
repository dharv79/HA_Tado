"""Dew point and mould risk tests."""

import pytest

from custom_components.tado_resume.comfort import dew_point, mould_risk
from tests.test_sensor import DEVICES_X, ROOM, _setup


@pytest.mark.parametrize(
    ("temp", "rh", "expected"),
    [(20.0, 50.0, 9.26), (25.0, 60.0, 16.69), (0.0, 100.0, 0.0), (10.0, 80.0, 6.71)],
)
def test_dew_point_matches_reference(temp, rh, expected) -> None:
    assert dew_point(temp, rh) == pytest.approx(expected, abs=0.05)


@pytest.mark.parametrize(("temp", "rh"), [(None, 50), (20, None), (20, 0), (20, 101)])
def test_dew_point_invalid(temp, rh) -> None:
    assert dew_point(temp, rh) is None
    assert mould_risk(temp, rh) is None


@pytest.mark.parametrize(
    ("temp", "rh", "level"),
    [(21, 45, "low"), (21, 62, "medium"), (21, 72, "high"), (12, 65, "medium")],
)
def test_mould_risk_levels(temp, rh, level) -> None:
    assert mould_risk(temp, rh) == level


async def test_comfort_sensors_created(hass) -> None:
    await _setup(hass, ROOM, DEVICES_X)
    assert float(hass.states.get("sensor.hall_dew_point").state) == pytest.approx(8.2, abs=0.1)
    assert hass.states.get("sensor.hall_mould_risk").state == "low"


async def test_comfort_sensors_classic_shape(hass) -> None:
    room = {
        **ROOM,
        "sensorDataPoints": {
            "insideTemperature": {"celsius": 19.5},
            "humidity": {"percentage": 48},
        },
    }
    await _setup(hass, room, None, "PRE_LINE_X")
    assert hass.states.get("sensor.hall_dew_point") is not None


async def test_no_humidity_no_comfort_sensors(hass) -> None:
    room = {**ROOM, "sensorDataPoints": {"insideTemperature": {"value": 19.5}}}
    await _setup(hass, room, None)
    assert hass.states.get("sensor.hall_dew_point") is None
    assert hass.states.get("sensor.hall_mould_risk") is None
