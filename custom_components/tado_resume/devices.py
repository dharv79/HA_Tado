"""Normalise tado device payloads (tado X roomsAndDevices, classic devices)."""

from __future__ import annotations

from typing import Any


def _connected(device: dict[str, Any]) -> bool | None:
    state = device.get("connectionState") or device.get("connection")
    if isinstance(state, dict):
        state = state.get("value", state.get("state"))
    if isinstance(state, bool):
        return state
    if isinstance(state, str):
        return state.upper() == "CONNECTED"
    return None


def parse_devices(raw: Any) -> list[dict[str, Any]]:
    """Return [{serial, type, room_id, battery_low, connected, firmware}].

    Missing fields are None so that entities are only created where data exists.
    """
    items: list[tuple[dict[str, Any], int | None]] = []
    if isinstance(raw, dict):
        for room in raw.get("rooms") or []:
            for device in room.get("devices") or []:
                items.append((device, room.get("roomId", room.get("id"))))
        for device in raw.get("unassignedDevices") or []:
            items.append((device, None))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item.get("devices"), list):
                for device in item["devices"]:
                    items.append((device, item.get("roomId", item.get("id"))))
            else:
                items.append((item, None))
    result = []
    for device, room_id in items:
        serial = device.get("serialNumber") or device.get("serialNo")
        if not serial:
            continue
        battery = device.get("batteryState")
        result.append(
            {
                "serial": serial,
                "type": device.get("deviceType") or device.get("type"),
                "room_id": room_id,
                "battery_low": None if battery is None else battery != "NORMAL",
                "connected": _connected(device),
                "firmware": device.get("firmwareVersion")
                or device.get("currentFwVersion"),
            }
        )
    return result
