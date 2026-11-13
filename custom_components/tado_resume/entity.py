"""Shared device info, base entities and helpers."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import TadoError
from .const import DOMAIN
from .coordinator import TadoCoordinator

if TYPE_CHECKING:
    from . import TadoResumeConfigEntry, TadoResumeData

MANUFACTURER = "tado°"


def home_device_info(home_id: int) -> DeviceInfo:
    """Device registry entry for home-level entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{home_id}_home")},
        name="Tado home",
        manufacturer=MANUFACTURER,
    )


def room_device_info(home_id: int, room_id: int, name: str | None = None) -> DeviceInfo:
    """Device registry entry shared by all entities of a room."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{home_id}_{room_id}")},
        name=name,
        manufacturer=MANUFACTURER,
    )


def physical_device_info(home_id: int, device: dict[str, Any]) -> DeviceInfo:
    """Device registry entry for a physical tado device."""
    info = DeviceInfo(
        identifiers={(DOMAIN, device["serial"])},
        name=f"tado {device['type'] or 'device'} {device['serial']}",
        manufacturer=MANUFACTURER,
        model=device["type"],
        sw_version=device["firmware"],
    )
    if device["room_id"] is not None:
        info["via_device"] = (DOMAIN, f"{home_id}_{device['room_id']}")
    return info


def number(value: Any) -> float | None:
    """Return a float for numeric payload values, else None."""
    return float(value) if isinstance(value, (int, float)) else None


def heating_power(room: dict[str, Any]) -> float | None:
    """Heating power percentage of a room (tado X and classic shapes)."""
    power = room.get("heatingPower")
    if power is None:
        power = (room.get("activityDataPoints") or {}).get("heatingPower")
    return number((power or {}).get("percentage"))


async def async_run(
    data: TadoResumeData, request: Awaitable[Any], what: str = "tado request"
) -> None:
    """Await a write request, surface failures to the user, then refresh."""
    try:
        await request
    except TadoError as err:
        raise HomeAssistantError(f"{what} failed: {err}") from err
    await data.coordinator.async_request_refresh()


class TadoEntity(CoordinatorEntity[TadoCoordinator]):
    """Base for coordinator-backed entities."""

    _attr_has_entity_name = True

    def __init__(self, entry: TadoResumeConfigEntry) -> None:
        self._data = entry.runtime_data
        self._options = entry.options
        super().__init__(self._data.coordinator)

    @property
    def _state(self) -> dict[str, Any]:
        return self.coordinator.data or {}


class TadoRoomEntity(TadoEntity):
    """Base for entities of one room."""

    def __init__(
        self, entry: TadoResumeConfigEntry, room_id: int, room_name: str | None, key: str
    ) -> None:
        super().__init__(entry)
        self._room_id = room_id
        home_id = self._data.home_id
        self._attr_unique_id = f"{home_id}_{room_id}_{key}"
        self._attr_device_info = room_device_info(home_id, room_id, room_name)

    @property
    def _room(self) -> dict[str, Any]:
        return self._state.get("rooms", {}).get(self._room_id, {})

    @property
    def available(self) -> bool:
        return super().available and bool(self._room)


class TadoDeviceEntity(TadoEntity):
    """Base for diagnostic entities of one physical device."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: TadoResumeConfigEntry, serial: str, key: str) -> None:
        super().__init__(entry)
        self._serial = serial
        home_id = self._data.home_id
        self._attr_unique_id = f"{home_id}_{serial}_{key}"
        device = self._device or {"serial": serial, "type": None, "room_id": None, "firmware": None}
        self._attr_device_info = physical_device_info(home_id, device)

    @property
    def _device(self) -> dict[str, Any] | None:
        return self.coordinator.devices.get(self._serial)

    @property
    def available(self) -> bool:
        return super().available and self._device is not None
