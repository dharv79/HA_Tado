# Phase 5: Device settings (0.7.0)

Features: F14 temperature offset, F15 child lock, F16 display and LED options.

## Scope
- `number` entity for temperature offset per device (bounds from the API).
- `switch` for child lock.
- Display or LED controls where the device model supports them.

## Discovery
Confirm which settings tado X allows writing per device type; settings are persistent device configuration, so writes need clear naming and tests for bounds.

## Exit criteria
Values round-trip on hardware; unsupported devices get no entity.

## Outcome (0.13.0)
Shipped as 0.13.0 because 0.7.0 to 0.12.0 were already used.
- `number` temperature offset (tado X, -10 to 10 °C, step 0.1) and `switch` child lock (tado X and classic), both in the configuration category, created only when the device payload reports the field (`temperatureOffset`, `childLockEnabled`).
- Writes: tado X `PATCH /homes/{id}/roomsAndDevices/devices/{serial}` with `temperatureOffset` or `childLockEnabled`; classic `PUT /devices/{serial}/childLock`. State refreshes after each write.
- Classic offset not implemented: it needs a per-device read endpoint, which adds API calls.
- Display and LED controls not implemented: no write endpoint identified.
- Not verified on hardware: the write endpoints and bodies, the offset bounds, and which device types report these fields on tado X.
