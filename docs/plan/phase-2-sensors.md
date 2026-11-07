# Phase 2: Sensors and diagnostics (0.4.0)

Features: F10 heating power, F11 battery and connectivity, F12 bridge and firmware, F13 early start.

## Scope
- Per-room sensors: heating power (%), humidity.
- Per-device binary sensors: low battery, connectivity. Diagnostic category.
- Bridge status and firmware version with an update-available indicator.
- Early start: read state and toggle where supported.

## Discovery
Identify which fields tado X exposes for each item; omit entities for fields that are absent.

## Exit criteria
Entities appear only where the data exists; fixtures cover both generations.

## Status (0.4.0)
Implemented: heating power and humidity sensors per room; firmware sensor, low battery and connectivity binary sensors per device (diagnostic). Entities are created only where the payload carries the field. Device payloads are normalised in `devices.py` (tado X `roomsAndDevices` and classic `devices`).

Not implemented, pending discovery on hardware: early start (read and toggle) and a firmware update-available indicator. No endpoint or field for either has been verified.

Unverified on hardware: all payload field names in `devices.py` come from desk research and the test fixtures.
