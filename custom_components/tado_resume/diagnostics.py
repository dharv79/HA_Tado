"""Diagnostics with credentials and personal data redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TadoResumeConfigEntry

TO_REDACT = {
    "refresh_token",
    "access_token",
    "home_id",
    "serialNo",
    "serialNumber",
    "shortSerialNo",
    "name",
    "email",
    "username",
    "location",
    "latitude",
    "longitude",
    "ssid",
    "macAddress",
    "ipAddress",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TadoResumeConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for the entry."""
    coordinator = entry.runtime_data.coordinator
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "generation": entry.runtime_data.generation,
        "capabilities": {str(rid): sorted(caps) for rid, caps in coordinator.capabilities.items()},
        "state": async_redact_data(coordinator.data or {}, TO_REDACT),
    }
