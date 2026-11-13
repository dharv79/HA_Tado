# Phase 6: Schedules (0.8.0)

Features: F17 schedule viewer, F18 schedule editing.

## Scope
- Sensor per room: next scheduled change time and target temperature.
- Service to change time blocks. Highest risk: it modifies stored configuration.

## Discovery
Confirm tado X schedule read and write endpoints. If write support is absent or unsafe, ship F17 only and record F18 as blocked here.

## Exit criteria
Next-change sensor matches the tado app; any edit service validates input and was tested on a single room first.

## Outcome (0.15.0)
Shipped as 0.15.0 (the 0.8.0 label is stale). F17 partial, F18 blocked.

- Classic only: `GET /homes/{home}/zones/{zone}/schedule/activeTimetable` (id, type) then `.../timetables/{id}/blocks` (dayType, start, setting). Cached per zone for one hour; merged into the room payload as `schedule`; failures keep the last value.
- Sensors per room with the schedule capability: `Next schedule change` (timestamp, attribute `power`) and `Next scheduled temperature`. The next change is the first future block start whose setting differs from the one in force, looking up to a week ahead; computed in Home Assistant's time zone.
- Day types: ONE_DAY = MONDAY_TO_SUNDAY; THREE_DAY = MONDAY_TO_FRIDAY, SATURDAY, SUNDAY; SEVEN_DAY = weekday names.
- Blocked: tado X schedule read and write endpoints could not be confirmed from public sources; editing (F18) was not attempted. Both need a traffic capture from the tado app before implementation.
- Not verified on hardware: classic response shapes, and agreement with the tado app.
