# Phase 3: Presence and open windows (0.5.0)

Features: F5 open-window handling, F6 Home/Away control, F7 per-device geofencing.

## Scope
- Binary sensor for open-window detection per room; actions to activate or cancel open-window mode.
- Home/Away select or switch, and a toggle between geofencing and manual presence.
- Device tracker per mobile device with location tracking enabled.

## Discovery
Confirm presence write endpoints on tado X, whether mobile device location is exposed, and the open-window activate/reset calls.

## Exit criteria
Presence changes reflect in tado app and back in Home Assistant; trackers appear only for opted-in devices.
