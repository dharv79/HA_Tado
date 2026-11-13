# Phase 11: Override details (0.13.0)

Know when an override ends.

## Scope
- Sensors: override ends at and time remaining; attributes for termination type.
- Timestamp sensor from the room payload (`manualControlTermination`/`overlay.termination`).

## Discovery
Confirm termination field names and time format on tado X and classic.

## Exit criteria
Sensor matches the tado app for timed, next-block and manual overrides.

## Outcome (0.14.0)
Shipped as 0.14.0 (0.13.0 was already used).

- Per room with the override capability: `Override ends` (timestamp, attribute `termination` = timer / next_schedule_block / manual) and `Override time remaining` (duration, seconds, displayed in minutes).
- Source: tado X `manualControlTermination`; classic `overlay.termination`. Types map `TIMER`, `NEXT_TIME_BLOCK`/`TADO_MODE`, `MANUAL`.
- End time prefers `projectedExpiry`/`expiry`; otherwise last successful poll plus `remainingTimeInSeconds`. Manual overrides have no end, so both sensors are unknown.
- Not verified on hardware: field names (`projectedExpiry`, `expiry`, `remainingTimeInSeconds`), and agreement with the tado app for each override type.
