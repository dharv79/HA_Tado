# Phase 11: Override details (0.13.0)

Know when an override ends.

## Scope
- Sensors: override ends at and time remaining; attributes for termination type.
- Timestamp sensor from the room payload (`manualControlTermination`/`overlay.termination`).

## Discovery
Confirm termination field names and time format on tado X and classic.

## Exit criteria
Sensor matches the tado app for timed, next-block and manual overrides.
