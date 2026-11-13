"""Blueprints import and run."""

import shutil
from pathlib import Path

import homeassistant.components.automation.config  # noqa: F401
import pytest
from homeassistant.components import automation
from homeassistant.components.blueprint import models
from homeassistant.setup import async_setup_component
from homeassistant.util import yaml as yaml_util
from pytest_homeassistant_custom_component.common import async_mock_service

SOURCE = Path(__file__).parent.parent / "blueprints" / "automation" / "tado_resume"
NAMES = ("window_open_heating_off", "everyone_away", "arrival_resume_schedule")


@pytest.fixture(autouse=True)
def install_blueprints(hass):
    target = Path(hass.config.path("blueprints/automation/tado_resume"))
    target.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        shutil.copy(SOURCE / f"{name}.yaml", target)


async def _setup(hass, name, inputs):
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "use_blueprint": {"path": f"tado_resume/{name}.yaml", "input": inputs},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.mark.parametrize("name", NAMES)
def test_blueprint_valid(name):
    data = yaml_util.load_yaml(str(SOURCE / f"{name}.yaml"))
    blueprint = models.Blueprint(
        data,
        expected_domain=automation.DOMAIN,
        schema=automation.config.AUTOMATION_BLUEPRINT_SCHEMA,
    )
    assert blueprint.inputs


async def test_window_open_then_closed(hass):
    off = async_mock_service(hass, "climate", "turn_off")
    resume = async_mock_service(hass, "tado_resume", "resume_schedule")
    await _setup(
        hass,
        "window_open_heating_off",
        {
            "window": "binary_sensor.window",
            "room": "climate.hall",
            "resume": "button.hall_resume",
            "delay": 0,
        },
    )
    hass.states.async_set("binary_sensor.window", "off")
    await hass.async_block_till_done()
    hass.states.async_set("binary_sensor.window", "on")
    await hass.async_block_till_done()
    assert [c.data["entity_id"] for c in off] == [["climate.hall"]]
    hass.states.async_set("binary_sensor.window", "off")
    await hass.async_block_till_done()
    assert [c.data["entity_id"] for c in resume] == [["button.hall_resume"]]


async def test_everyone_away(hass):
    select = async_mock_service(hass, "select", "select_option")
    await _setup(
        hass,
        "everyone_away",
        {
            "people": ["person.a", "person.b"],
            "presence": "select.tado_home_presence",
            "delay": 0,
        },
    )
    hass.states.async_set("person.a", "home")
    hass.states.async_set("person.b", "home")
    await hass.async_block_till_done()
    hass.states.async_set("person.a", "not_home")
    await hass.async_block_till_done()
    assert not select
    hass.states.async_set("person.b", "not_home")
    await hass.async_block_till_done()
    assert [c.data["option"] for c in select] == ["away"]


async def test_arrival_resumes(hass):
    select = async_mock_service(hass, "select", "select_option")
    resume = async_mock_service(hass, "tado_resume", "resume_all_schedules")
    await _setup(
        hass,
        "arrival_resume_schedule",
        {"people": ["person.a"], "presence": "select.tado_home_presence"},
    )
    hass.states.async_set("person.a", "not_home")
    await hass.async_block_till_done()
    hass.states.async_set("person.a", "home")
    await hass.async_block_till_done()
    assert [c.data["option"] for c in select] == ["auto"]
    assert len(resume) == 1
