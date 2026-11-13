"""Derived comfort values: dew point and mould risk (no API calls)."""

from __future__ import annotations

import math

# Magnus formula constants (valid roughly -45 to 60 degrees Celsius).
_MAGNUS_A = 17.62
_MAGNUS_B = 243.12

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
MOULD_RISK_LEVELS = [RISK_LOW, RISK_MEDIUM, RISK_HIGH]

# Thresholds: relative humidity (%) and margin between air and dew point (K).
_HIGH_HUMIDITY = 70.0
_MEDIUM_HUMIDITY = 60.0
_HIGH_MARGIN = 3.0
_MEDIUM_MARGIN = 5.0


def dew_point(temperature: float | None, humidity: float | None) -> float | None:
    """Dew point in Celsius from air temperature and relative humidity."""
    if temperature is None or humidity is None or not 0 < humidity <= 100:
        return None
    gamma = math.log(humidity / 100) + _MAGNUS_A * temperature / (_MAGNUS_B + temperature)
    return _MAGNUS_B * gamma / (_MAGNUS_A - gamma)


def mould_risk(temperature: float | None, humidity: float | None) -> str | None:
    """Mould risk level from humidity and the air/dew-point margin."""
    point = dew_point(temperature, humidity)
    if point is None or temperature is None or humidity is None:
        return None
    margin = temperature - point
    if humidity >= _HIGH_HUMIDITY or margin < _HIGH_MARGIN:
        return RISK_HIGH
    if humidity >= _MEDIUM_HUMIDITY or margin < _MEDIUM_MARGIN:
        return RISK_MEDIUM
    return RISK_LOW
