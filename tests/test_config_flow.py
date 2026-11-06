"""Config flow tests."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tado_resume.api import TadoAuthPending
from custom_components.tado_resume.const import DOMAIN

DEVICE = {
    "device_code": "dc",
    "user_code": "ABC",
    "verification_uri_complete": "https://login.tado.com/device?user_code=ABC",
}
P = "custom_components.tado_resume.config_flow"


async def test_flow_creates_entry(hass: HomeAssistant) -> None:
    with (
        patch(f"{P}.async_start_device_flow", AsyncMock(return_value=DEVICE)),
        patch(
            f"{P}.async_poll_device_flow",
            AsyncMock(side_effect=[TadoAuthPending("p"), {"refresh_token": "r"}]),
        ),
        patch(f"{P}.TadoApi.async_get_homes", AsyncMock(return_value=[{"id": 1, "name": "Home"}])),
        patch(f"{P}.TadoApi.async_get_generation", AsyncMock(return_value="LINE_X")),
        patch("custom_components.tado_resume.async_setup_entry", AsyncMock(return_value=True)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["errors"] == {"base": "not_authorised"}
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "home_id": 1,
        "generation": "LINE_X",
        "refresh_token": "r",
    }


async def test_rotated_refresh_token_is_stored(hass: HomeAssistant) -> None:
    """The token rotated during setup, not the original, must be saved."""

    async def fake_homes(self):
        await self._token_updated("rotated")
        return [{"id": 1, "name": "Home"}]

    with (
        patch(f"{P}.async_start_device_flow", AsyncMock(return_value=DEVICE)),
        patch(f"{P}.async_poll_device_flow", AsyncMock(return_value={"refresh_token": "old"})),
        patch(f"{P}.TadoApi.async_get_homes", fake_homes),
        patch(f"{P}.TadoApi.async_get_generation", AsyncMock(return_value="LINE_X")),
        patch("custom_components.tado_resume.async_setup_entry", AsyncMock(return_value=True)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["data"]["refresh_token"] == "rotated"
