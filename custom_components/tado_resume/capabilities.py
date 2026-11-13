"""Capability map: what each room of a home can read or write.

Later phases use this to create only the entities a room supports.
"""

from __future__ import annotations

from typing import Any

CAP_RESUME = "resume"
CAP_TEMPERATURE = "temperature"
CAP_HUMIDITY = "humidity"
CAP_TARGET = "target_temperature"
CAP_HEATING_POWER = "heating_power"
CAP_OPEN_WINDOW = "open_window"
CAP_OVERRIDE = "override"
CAP_SCHEDULE = "schedule"


def room_capabilities(room: dict[str, Any]) -> frozenset[str]:
    """Derive the capabilities of one room from its state payload.

    Handles tado X (sensorDataPoints, manualControlTermination) and classic
    (sensorDataPoints, overlay) shapes; both expose the shared keys below.
    """
    caps = {CAP_RESUME}
    points = room.get("sensorDataPoints") or {}
    if "insideTemperature" in points:
        caps.add(CAP_TEMPERATURE)
    if "humidity" in points:
        caps.add(CAP_HUMIDITY)
    setting = room.get("setting") or {}
    if {"temperature", "type", "power"} & setting.keys():
        caps.add(CAP_TARGET)
    if "heatingPower" in room or "heatingPower" in points:
        caps.add(CAP_HEATING_POWER)
    if "openWindow" in room or "openWindowDetected" in room:
        caps.add(CAP_OPEN_WINDOW)
    if "manualControlTermination" in room or "overlay" in room:
        caps.add(CAP_OVERRIDE)
    if room.get("schedule"):
        caps.add(CAP_SCHEDULE)
    return frozenset(caps)


def capability_map(state: dict[str, Any]) -> dict[int, frozenset[str]]:
    """Return {room_id: capabilities} for a coordinator snapshot."""
    return {rid: room_capabilities(room) for rid, room in state["rooms"].items()}
