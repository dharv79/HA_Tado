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

## Status (0.5.0)
Implemented: Presence select (home, away, automatic) per home; open-window binary sensor, with activate and cancel buttons, per room that reports `openWindow`/`openWindowDetected`; a device tracker per mobile device with `geoTrackingEnabled` (from `mobileDevices`). Entities appear only where the payload has the data.

Requests (desk research, unverified on hardware): tado X `PUT /presence` with `homePresence` HOME/AWAY/AUTO; classic `PUT`/`DELETE presenceLock`; open window `POST`/`DELETE rooms/{id}/openWindow` (X) and `POST .../state/openWindow/activate`, `DELETE .../state/openWindow` (classic).
Deferred: a separate geofencing toggle (covered by the "Automatic" option).
