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
