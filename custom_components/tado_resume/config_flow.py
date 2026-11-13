"""Config flow using the tado device-code login."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    TadoApi,
    TadoAuthError,
    TadoAuthPending,
    TadoError,
    async_poll_device_flow,
    async_start_device_flow,
)
from .const import CONF_GENERATION, CONF_HOME_ID, CONF_REFRESH_TOKEN, DOMAIN


class TadoResumeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._device: dict[str, Any] = {}
        self._refresh_token: str | None = None
        self._homes: list[dict[str, Any]] = []
        self._api: TadoApi | None = None

    async def _async_login(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult | None:
        """Run the device login; return a form/abort, or None once logged in."""
        session = async_get_clientsession(self.hass)
        errors: dict[str, str] = {}
        if user_input is None or not self._device:
            try:
                self._device = await async_start_device_flow(session)
            except TadoError:
                return self.async_abort(reason="cannot_connect")
        else:
            try:
                tokens = await async_poll_device_flow(session, self._device["device_code"])
            except TadoAuthPending:
                errors["base"] = "not_authorised"
            except TadoAuthError:
                self._device = {}
                return self.async_abort(reason="auth_failed")
            except TadoError:
                return self.async_abort(reason="cannot_connect")
            else:
                self._refresh_token = tokens["refresh_token"]
                return None

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "url": self._device.get("verification_uri_complete", ""),
                "code": self._device.get("user_code", ""),
            },
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Start the device login and show the URL to the user."""
        if (result := await self._async_login("user", user_input)) is not None:
            return result
        return await self._async_pick_home()

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start reauthentication after tado rejected the stored token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Repeat the device login and store the new refresh token."""
        if (result := await self._async_login("reauth_confirm", user_input)) is not None:
            return result
        entry = self._get_reauth_entry()

        async def _rotated(token: str) -> None:
            self._refresh_token = token

        api = TadoApi(async_get_clientsession(self.hass), self._refresh_token or "", _rotated)
        try:
            homes = await api.async_get_homes()
        except TadoAuthError:
            self._device = {}
            return self.async_abort(reason="auth_failed")
        except TadoError:
            return self.async_abort(reason="cannot_connect")
        if str(entry.data[CONF_HOME_ID]) not in {str(h["id"]) for h in homes}:
            return self.async_abort(reason="wrong_account")
        return self.async_update_reload_and_abort(
            entry, data_updates={CONF_REFRESH_TOKEN: self._refresh_token}
        )

    async def _async_pick_home(self) -> ConfigFlowResult:
        async def _rotated(token: str) -> None:
            # tado refresh tokens are single-use: keep the newest one.
            self._refresh_token = token

        # One client for the whole flow so a rotated token is never lost.
        api = self._api = TadoApi(
            async_get_clientsession(self.hass), self._refresh_token or "", _rotated
        )
        try:
            self._homes = await api.async_get_homes()
        except TadoError:
            return self.async_abort(reason="cannot_connect")
        if not self._homes:
            return self.async_abort(reason="no_homes")
        if len(self._homes) == 1:
            return await self._async_create(self._homes[0], api)
        return await self.async_step_home()

    async def async_step_home(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose a home when the account has several."""
        if user_input is not None:
            home = next(h for h in self._homes if str(h["id"]) == user_input["home"])
            assert self._api is not None
            return await self._async_create(home, self._api)
        return self.async_show_form(
            step_id="home",
            data_schema=vol.Schema(
                {vol.Required("home"): vol.In({str(h["id"]): h["name"] for h in self._homes})}
            ),
        )

    async def _async_create(self, home: dict[str, Any], api: TadoApi) -> ConfigFlowResult:
        await self.async_set_unique_id(str(home["id"]))
        self._abort_if_unique_id_configured()
        try:
            generation = await api.async_get_generation(home["id"])
        except TadoError:
            return self.async_abort(reason="cannot_connect")
        return self.async_create_entry(
            title=home["name"],
            data={
                CONF_HOME_ID: home["id"],
                CONF_GENERATION: generation,
                CONF_REFRESH_TOKEN: self._refresh_token,
            },
        )
