"""Options flow and its effect on behaviour."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.const import DOMAIN

from .test_climate import ENTITY, ROOM_X, _setup


async def test_options_flow_saves_values(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    new = {
        "poll_interval": 120,
        "boost_temperature": 23.0,
        "boost_minutes": 45,
        "default_termination": "indefinite",
    }
    with patch("custom_components.tado_resume.async_setup_entry", AsyncMock(return_value=True)):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=new
        )
    assert result["type"] == "create_entry"
    assert entry.options == new


async def test_defaults_unchanged_without_options(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    coordinator = entry.runtime_data.coordinator
    assert coordinator.update_interval == timedelta(seconds=60)
    assert entry.options == {}


async def test_poll_interval_option(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X, options={"poll_interval": 300})
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.runtime_data.coordinator.update_interval == timedelta(seconds=300)


async def test_boost_and_termination_options(hass: HomeAssistant, request) -> None:
    options = {"boost_temperature": 22.5, "boost_minutes": 10, "default_termination": "indefinite"}
    await _setup(hass, request, ROOM_X, options=options)
    with (
        patch("custom_components.tado_resume.TadoApi.async_boost_room", AsyncMock()) as boost,
        patch("custom_components.tado_resume.TadoApi.async_set_manual", AsyncMock()) as manual,
    ):
        await hass.services.async_call(
            "climate",
            "set_preset_mode",
            {"entity_id": ENTITY, "preset_mode": "boost"},
            blocking=True,
        )
        await hass.services.async_call(
            "climate", "set_temperature", {"entity_id": ENTITY, "temperature": 21}, blocking=True
        )
    boost.assert_awaited_once_with(1, "LINE_X", 5, 22.5, 600)
    manual.assert_awaited_once_with(1, "LINE_X", 5, 21.0, "indefinite", None, False)


async def test_options_change_reloads_entry(hass: HomeAssistant, request) -> None:
    await _setup(hass, request, ROOM_X)
    entry: MockConfigEntry = hass.config_entries.async_entries(DOMAIN)[0]
    with patch.object(hass.config_entries, "async_reload", AsyncMock()) as reload:
        hass.config_entries.async_update_entry(entry, options={"poll_interval": 90})
        await hass.async_block_till_done()
    reload.assert_awaited_once_with(entry.entry_id)
