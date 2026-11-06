"""Button and service tests."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_resume.const import DOMAIN


async def _setup(hass: HomeAssistant, generation: str = "LINE_X"):
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
        AsyncMock(return_value={"rooms": {5: {"id": 5}}}),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_room_button_resumes(hass: HomeAssistant) -> None:
    await _setup(hass)
    with patch(
        "custom_components.tado_resume.TadoApi.async_resume_room", AsyncMock()
    ) as resume, patch(
        "custom_components.tado_resume.coordinator.TadoCoordinator.async_request_refresh",
        AsyncMock(),
    ) as refresh:
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.hall_resume_schedule"},
            blocking=True,
        )
    resume.assert_awaited_once_with(1, "LINE_X", 5)
    refresh.assert_awaited_once()


async def test_resume_all_service(hass: HomeAssistant) -> None:
    await _setup(hass)
    with patch(
        "custom_components.tado_resume.TadoApi.async_resume_all", AsyncMock()
    ) as resume, patch(
        "custom_components.tado_resume.coordinator.TadoCoordinator.async_request_refresh",
        AsyncMock(),
    ) as refresh:
        await hass.services.async_call(
            DOMAIN, "resume_all_schedules", {}, blocking=True
        )
    resume.assert_awaited_once_with(1, "LINE_X", [5])
    refresh.assert_awaited_once()
